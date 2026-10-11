"""Real diskcache transactions enforce quotas across threads and processes."""
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from multiprocessing import get_context
from tempfile import TemporaryDirectory
from threading import Barrier
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings
from django.utils import timezone

from apps.family.throttles import reserve_invitation_attempt


def process_attempts(directory, barrier):
    with override_settings(ALFRED_FAMILY_INVITE_THROTTLE_DIR=directory):
        barrier.wait()
        return [reserve_invitation_attempt(42, "family_invite_accept", 3, 600) for _ in range(10)]


class FamilyInvitationAtomicTests(SimpleTestCase):
    def test_simultaneous_threads_reserve_exactly_the_configured_allowance(self):
        directory = self.enterContext(TemporaryDirectory(prefix="alfred-invite-threads-"))
        self.enterContext(override_settings(ALFRED_FAMILY_INVITE_THROTTLE_DIR=directory))
        now = timezone.now()
        barrier = Barrier(12, timeout=30)
        def attempt(_):
            barrier.wait()
            return reserve_invitation_attempt(42, "family_invite_create", 3, 600)
        with patch("django.utils.timezone.now", return_value=now), ThreadPoolExecutor(max_workers=12) as pool:
            outcomes = list(pool.map(attempt, range(12)))
        self.assertEqual(outcomes.count(0), 3)
        self.assertTrue(all(wait == 600 for wait in outcomes if wait))

    def test_processes_and_reopened_instances_share_the_same_strict_limit(self):
        directory = self.enterContext(TemporaryDirectory(prefix="alfred-invite-processes-"))
        context = get_context("spawn")
        with context.Manager() as manager, ProcessPoolExecutor(max_workers=4, mp_context=context) as pool:
            barrier = manager.Barrier(4, timeout=30)
            outcomes = [wait for batch in pool.map(process_attempts, [directory] * 4, [barrier] * 4) for wait in batch]
        self.assertEqual(outcomes.count(0), 3)
        self.assertTrue(all(wait > 0 for wait in outcomes if wait))
        with override_settings(ALFRED_FAMILY_INVITE_THROTTLE_DIR=directory):
            self.assertGreater(reserve_invitation_attempt(42, "family_invite_accept", 3, 600), 0)
            self.assertEqual(reserve_invitation_attempt(43, "family_invite_accept", 3, 600), 0)
            self.assertEqual(reserve_invitation_attempt(42, "family_invite_create", 3, 600), 0)
