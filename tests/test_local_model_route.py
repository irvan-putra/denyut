"""Synthetic routing tests: no network, model or native execution."""
import importlib.util
from pathlib import Path
from types import SimpleNamespace as NS
import threading
import sys
import deltachat2 as REAL_DELTACHAT2

path = Path(__file__).resolve().parents[1] / 'android/app/src/main/python/local_model_route.py'
spec = importlib.util.spec_from_file_location('local_route_under_test', path)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class Rpc:
    verified = True
    def get_contact(self, account, contact):
        return NS(is_verified=self.verified, is_key_contact=True, e2ee_avail=True,
                  is_blocked=False, address='synthetic@example.invalid')
    def get_full_chat_by_id(self, account, chat):
        return NS(chat_type='Single', is_encrypted=True, is_contact_request=False,
                  is_device_chat=False, is_self_talk=False, can_send=True, contact_ids=[42])

class Backend:
    def __init__(self):
        self.started = threading.Event()
        self.finish = threading.Event()
        self.calls = 0
    def complete(self, *_):
        self.calls += 1
        self.started.set()
        assert self.finish.wait(2)
        return 'synthetic answer'

def message(contact=42):
    return NS(text='synthetic', from_id=contact, chat_id=99, show_padlock=True, is_forwarded=False)

def test_unbound_unauthorized_and_forwarded_never_generate():
    backend, rpc = Backend(), Rpc()
    route = m.LocalModelRoute(backend, '')
    assert 'not configured' in route.offer(rpc, 1, message(), lambda *_: None)
    route.bind_owner(rpc, 1, 42, 99)
    assert 'limited' in route.offer(rpc, 1, message(43), lambda *_: None)
    msg = message(); msg.is_forwarded = True
    assert 'direct encrypted' in route.offer(rpc, 1, msg, lambda *_: None)
    assert backend.calls == 0

def test_one_worker_no_queue_and_revoke_suppresses_reply():
    backend, rpc, sent = Backend(), Rpc(), []
    route = m.LocalModelRoute(backend, '')
    route.bind_owner(rpc, 1, 42, 99)
    assert route.offer(rpc, 1, message(), lambda *args: sent.append(args)) is None
    assert backend.started.wait(1)  # caller did not block on model completion
    assert 'busy' in route.offer(rpc, 1, message(), lambda *_: None)
    route.revoke()
    backend.finish.set()
    # completion witnessed without sleeping on a timing guess
    for thread in threading.enumerate():
        if thread.name == 'denyut-local-model': thread.join(2)
    assert not sent and backend.calls == 1

def test_success_owner_reply_and_verification_loss():
    backend, rpc, sent = Backend(), Rpc(), []
    route = m.LocalModelRoute(backend, '')
    route.bind_owner(rpc, 1, 42, 99)
    route.offer(rpc, 1, message(), lambda *args: sent.append(args))
    assert backend.started.wait(1)
    backend.finish.set()
    for thread in threading.enumerate():
        if thread.name == 'denyut-local-model': thread.join(2)
    assert sent == [(1, 99, 'synthetic answer')]
    rpc.verified = False
    assert 'unavailable' in route.offer(rpc, 1, message(), lambda *_: None)
    assert backend.calls == 1

def test_adapter_command_runs_while_model_worker_blocked(tmp_path, monkeypatch):
    # Legacy host adapter test swaps sys.modules without restoration.
    # Restore the already-imported real dependency only for this test.
    monkeypatch.setitem(sys.modules, "deltachat2", REAL_DELTACHAT2)
    # Drive actual Android adapter's hook using real deltachat2 hook registration.
    from denyut.core import Assistant
    root = Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location('android_bot_local_route_test', root / 'android/app/src/main/python/android_bot.py')
    adapter = importlib.util.module_from_spec(spec); spec.loader.exec_module(adapter)
    assistant = Assistant(str(root / 'android/app/src/main/python/behavior.json'), str(tmp_path))
    backend, rpc, sent = Backend(), Rpc(), []
    rpc.send_msg = lambda account, chat, data: sent.append(data.text)
    route = m.LocalModelRoute(backend, assistant.system_prompt)
    route.bind_owner(rpc, 1, 42, 99)
    hook = list(adapter._make_hooks(assistant, rpc, route))[0][0]
    bot = NS(rpc=rpc)
    hook(bot, 1, NS(msg=message()))
    assert backend.started.wait(1)
    command = message(); command.text = '/echo commands still work'
    hook(bot, 1, NS(msg=command))
    assert sent == ['commands still work']
    route.close(); backend.finish.set()
    for thread in threading.enumerate():
        if thread.name == 'denyut-local-model': thread.join(2)
    assert sent == ['commands still work']

def test_explicit_picker_snapshot_revalidates_and_expires():
    rpc = Rpc()
    rpc.get_all_account_ids = lambda: [1]
    rpc.get_config = lambda *_: 'bot@example.invalid'
    rpc.get_chatlist_entries = lambda *_: [99]
    route = m.LocalModelRoute(Backend(), '')
    choices = route.owner_choices(rpc)
    assert len(choices) == 1
    assert 'synthetic@example.invalid' in choices[0]['label']
    old = choices[0]['token']
    route.owner_choices(rpc)
    import pytest
    with pytest.raises(ValueError): route.select_owner(rpc, old)
    choice = route.owner_choices(rpc)[0]['token']
    rpc.verified = False
    with pytest.raises(ValueError): route.select_owner(rpc, choice)
    assert route._owner is None
    rpc.verified = True
    route.select_owner(rpc, route.owner_choices(rpc)[0]['token'])
    assert route._owner[:3] == (1, 42, 99)
    route.revoke()
    assert route._owner is None

def test_pending_confirmation_and_nonowner_help_preserved(tmp_path, monkeypatch):
    monkeypatch.setitem(sys.modules, 'deltachat2', REAL_DELTACHAT2)
    from denyut.core import Assistant, Confirm
    root = Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location('android_bot_confirm_test', root / 'android/app/src/main/python/android_bot.py')
    adapter = importlib.util.module_from_spec(spec); spec.loader.exec_module(adapter)
    assistant = Assistant(str(root / 'android/app/src/main/python/behavior.json'), str(tmp_path))
    backend, rpc, sent = Backend(), Rpc(), []
    rpc.send_msg = lambda account, chat, data: sent.append(data.text)
    route = m.LocalModelRoute(backend, assistant.system_prompt)
    route.bind_owner(rpc, 1, 42, 99)
    hook = list(adapter._make_hooks(assistant, rpc, route))[0][0]
    assistant._pending['42'] = Confirm('synthetic?', lambda: 'confirmed')
    msg = message(); msg.text = 'yes'
    hook(NS(rpc=rpc), 1, NS(msg=msg))
    assert sent == ['confirmed'] and '42' not in assistant._pending
    msg = message(43); msg.text = 'hello'
    hook(NS(rpc=rpc), 1, NS(msg=msg))
    assert 'No model is configured' in sent[-1]
    assert backend.calls == 0


def test_real_258_types_parse_and_route_fields():
    from deltachat2.types import Contact, FullChat, ChatType, _from_dict
    # Minimal valid 2.58 server shapes, parsed by the actual pinned parser.
    contact = _from_dict(Contact, {
        'address': 'synthetic@example.invalid', 'auth_name': '', 'color': '#000000',
        'display_name': 'Synthetic', 'e2ee_avail': True, 'id': 42, 'is_blocked': False,
        'is_bot': False, 'is_key_contact': True, 'is_verified': True, 'last_seen': 0,
        'name': 'Synthetic', 'name_and_addr': 'Synthetic', 'status': '', 'was_seen_recently': False})
    chat = _from_dict(FullChat, {
        'archived': False, 'can_send': True, 'chat_type': 'Single', 'color': '#000000',
        'contact_ids': [42], 'ephemeral_timer': 0, 'fresh_message_counter': 0, 'id': 99,
        'is_contact_request': False, 'is_device_chat': False, 'is_encrypted': True,
        'is_muted': False, 'is_self_talk': False, 'is_unpromoted': False, 'name': 'Synthetic',
        'past_contact_ids': [], 'pinned': False, 'self_in_group': False, 'was_seen_recently': False})
    assert chat.chat_type is ChatType.SINGLE
    rpc = NS(get_contact=lambda *_: contact, get_full_chat_by_id=lambda *_: chat)
    assert m.LocalModelRoute._check_peer(rpc, 1, 42, 99) == 'synthetic@example.invalid'
    contact.is_verified = False
    import pytest
    with pytest.raises(ValueError): m.LocalModelRoute._check_peer(rpc, 1, 42, 99)

def test_slow_send_does_not_block_revoke_or_close():
    backend, rpc = Backend(), Rpc()
    route = m.LocalModelRoute(backend, '')
    route.bind_owner(rpc, 1, 42, 99)
    sending, finish_send = threading.Event(), threading.Event()
    delivered = []
    def send(*args):
        sending.set()
        assert finish_send.wait(2)
        delivered.append(args)
    route.offer(rpc, 1, message(), send)
    assert backend.started.wait(1)
    backend.finish.set()
    assert sending.wait(1)
    revoked = threading.Event()
    def revoke():
        route.revoke()
        route.close()
        revoked.set()
    thread = threading.Thread(target=revoke)
    thread.start()
    assert revoked.wait(1), 'slow transport must not hold owner state lock'
    finish_send.set()
    thread.join(2)
    for worker in threading.enumerate():
        if worker.name == 'denyut-local-model': worker.join(2)
    # A send committed before revoke cannot be retracted. This is explicit,
    # unlike claiming revoke cancels an RPC already in progress.
    assert delivered == [(1, 99, 'synthetic answer')]
    assert route.owns_message(1, message()) is False
