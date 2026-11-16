"""Session-only owner binding and one in-flight local model worker.

bind_owner is an owner-device setup API, NOT an inbound command. No identity is
inferred from display names, message text, quotes or first contact. A future
owner picker must show/re-confirm the existing verified contact. No account or
contact is created/modified by this module. Bindings never survive restart.
"""
import threading


class LocalModelRoute:
    def __init__(self, backend, system_prompt):
        self.backend = backend
        self.system = system_prompt
        self._lock = threading.Lock()
        self._owner = None
        self._generation = 0
        self._busy = False
        self._closed = False
        self._choices = {}
        self._choice_epoch = 0

    @staticmethod
    def _check_peer(rpc, account, contact, chat):
        peer = rpc.get_contact(account, contact)
        room = rpc.get_full_chat_by_id(account, chat)
        if not (peer.is_verified and peer.is_key_contact and peer.e2ee_avail
                and not peer.is_blocked and room.chat_type == "Single"
                and room.is_encrypted and not room.is_contact_request
                and not room.is_device_chat and not room.is_self_talk
                and room.can_send and room.contact_ids == [contact]):
            raise ValueError("Select an existing verified encrypted one-to-one peer")
        return peer.address

    def bind_owner(self, rpc, account, contact, chat):
        # Only local owner setup calls this. A process-local epoch invalidates
        # in-flight replies on rebind/revoke/stop. Revalidate current peer data.
        address = self._check_peer(rpc, account, contact, chat)
        with self._lock:
            if self._closed:
                raise ValueError("Model route closed")
            self._owner = (account, contact, chat, address)
            self._generation += 1

    def owner_choices(self, rpc):
        """Local owner picker only. Read existing state, never create/pair contacts.
        UI receives full account/contact address, not just ambiguous names.
        Refresh expires every previous snapshot selection token.
        """
        found = []
        for account in rpc.get_all_account_ids():
            own_address = rpc.get_config(account, "addr")
            for chat in rpc.get_chatlist_entries(account, None, None, None)[:200]:
                room = rpc.get_full_chat_by_id(account, chat)
                if len(room.contact_ids) != 1:
                    continue
                contact = room.contact_ids[0]
                try:
                    address = self._check_peer(rpc, account, contact, chat)
                except Exception:
                    continue
                found.append((account, contact, chat, address, own_address))
        with self._lock:
            if self._closed:
                return []
            self._choice_epoch += 1
            self._choices = {f"{self._choice_epoch}:{i}": item[:4] for i, item in enumerate(found)}
            return [{"token": token, "label": f"Account {item[4]} / verified peer {item[3]}"}
                    for (token, _), item in zip(self._choices.items(), found)]

    def select_owner(self, rpc, token):
        with self._lock:
            choice = self._choices.get(token)
            if choice is None or self._closed:
                raise ValueError("Owner choice expired; refresh the device picker")
            self._choices = {}
        if self._check_peer(rpc, *choice[:3]) != choice[3]:
            raise ValueError("Owner choice changed; refresh the device picker")
        self.bind_owner(rpc, *choice[:3])

    def revoke(self):
        with self._lock:
            self._owner = None
            self._choices = {}
            self._generation += 1

    def close(self):
        with self._lock:
            self._closed = True
            self._owner = None
            self._choices = {}
            self._generation += 1

    def owns_message(self, account, message):
        with self._lock:
            return (not self._closed and self._owner is not None
                    and self._owner[:3] == (account, message.from_id, message.chat_id))

    def offer(self, rpc, account, message, send):
        """Return immediately; one worker, no queue, no history or skill mutation.
        Caller sends returned status if any. None means a worker owns the reply.
        An unbound/unauthorized request never reaches native model code.
        """
        text = (message.text or "").strip()
        with self._lock:
            owner = self._owner
            epoch = self._generation
            if self._closed or owner is None:
                return "Local model owner is not configured on the device. Commands still work."
            if owner[:3] != (account, message.from_id, message.chat_id):
                return "Local model access is limited to its configured owner."
            if not getattr(message, "show_padlock", False) or getattr(message, "is_forwarded", True):
                return "Local model requires a direct encrypted owner message."
            if self._busy:
                return "Local model is busy; try again later. Commands still work."
            if len(text) + len(self.system) > 1500:
                return "That message is too long for the local trial."
            self._busy = True
        try:
            if self._check_peer(rpc, *owner[:3]) != owner[3]:
                raise ValueError("Owner changed")
        except Exception:
            with self._lock:
                self._busy = False
            return "Local model owner verification is unavailable."

        def work():
            try:
                reply = self.backend.complete(self.system, [], text)
                # Recheck both session grant and current verified route before
                # disclosure. No native lock held while issuing transport calls.
                if self._check_peer(rpc, *owner[:3]) != owner[3]:
                    return
                with self._lock:
                    if self._closed or epoch != self._generation or self._owner != owner:
                        return
                # The decision is committed at the epoch check above. Do not
                # hold the state lock during RPC: revoke/close must remain
                # responsive. A send already committed/in progress cannot be
                # retracted; revocation only prevents later send decisions.
                send(account, message.chat_id, reply)
            except Exception:
                # Do not leak inputs, addresses, model paths or diagnostics.
                pass
            finally:
                with self._lock:
                    self._busy = False
        threading.Thread(target=work, name="denyut-local-model", daemon=True).start()
        return None
