import json
import unittest
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest import mock

from utils import ephemeral
from utils.ephemeral import player_combat_report, send_ephemeral_reply

BOT = SimpleNamespace(token='123:TEST')
CALL = SimpleNamespace(id='cbq-1')
NOW = datetime(2026, 11, 10, 12, 0, 0)


def fighter(**over):
    base = dict(health=100, max_health=100, current_hp=80, mana=30, max_mana=50, shield_hp=0, speed=0,
                last_attack_time=None)
    base.update(over)
    return SimpleNamespace(**base)


class TestSendEphemeralReply(unittest.TestCase):
    def test_replies_to_the_callback_without_a_chat_id(self):
        with mock.patch.object(ephemeral.apihelper, '_make_request') as request:
            self.assertTrue(send_ephemeral_reply(BOT, CALL, "ciao"))
        (token, method), kwargs = request.call_args
        self.assertEqual((token, method), ('123:TEST', 'sendMessage'))
        self.assertNotIn('chat_id', kwargs['params'])
        self.assertEqual(json.loads(kwargs['params']['ephemeral_message_parameters']), {'callback_query_id': 'cbq-1'})
        self.assertEqual(kwargs['params']['parse_mode'], 'Markdown')

    def test_a_refused_call_tells_the_caller_to_fall_back(self):
        with mock.patch.object(ephemeral.apihelper, '_make_request', side_effect=Exception("Bad Request")):
            self.assertFalse(send_ephemeral_reply(BOT, CALL, "ciao"))

    def test_broken_markdown_is_sent_again_as_plain_text(self):
        with mock.patch.object(ephemeral.apihelper, '_make_request',
                               side_effect=[Exception("can't parse entities"), None]) as request:
            self.assertTrue(send_ephemeral_reply(BOT, CALL, "a_b"))
        self.assertEqual(request.call_count, 2)
        self.assertNotIn('parse_mode', request.call_args.kwargs['params'])

    def test_the_switch_turns_it_off(self):
        with mock.patch.dict('os.environ', {'EPHEMERAL_COMBAT': '0'}), \
                mock.patch.object(ephemeral.apihelper, '_make_request') as request:
            self.assertFalse(send_ephemeral_reply(BOT, CALL, "ciao"))
        request.assert_not_called()


class TestPlayerCombatReport(unittest.TestCase):
    def test_ready_fighter(self):
        report = player_combat_report(fighter(), now=NOW)
        self.assertIn("❤️ 80/100", report)
        self.assertIn("💙 30/50", report)
        self.assertIn("✅ Puoi agire subito", report)
        self.assertNotIn("Scudo", report)

    def test_cooldown_follows_speed_and_the_aoe_doubling(self):
        just_attacked = fighter(speed=20, last_attack_time=NOW - timedelta(seconds=10))
        self.assertIn("tra 21s", player_combat_report(just_attacked, now=NOW))
        self.assertIn("tra 51s", player_combat_report(just_attacked, cooldown_multiplier=2, now=NOW))

    def test_falls_back_to_health_and_warns_when_low(self):
        report = player_combat_report(fighter(current_hp=None, health=20, shield_hp=15), now=NOW)
        self.assertIn("❤️ 20/100", report)
        self.assertIn("🛡️ Scudo: 15", report)
        self.assertIn("⚠️", report)

    def test_knocked_out(self):
        self.assertIn("💀", player_combat_report(fighter(current_hp=0), now=NOW))


if __name__ == '__main__':
    unittest.main()
