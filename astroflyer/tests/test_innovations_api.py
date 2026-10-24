"""
AstroFlyer HEO - /api/propagate reports the ECR-MF tiers and covariance steering of the run it made.

Identical requests must give identical innovation reports (nothing random), and the
reports must match what the engine itself returns for the same run.
"""

import json
import threading
import unittest
import urllib.error
import urllib.request

import numpy as np

from astroflyer.backend.app_server import create_server
from astroflyer.backend.astro_engine import ThirdReviewEngine, keplerian_to_cartesian

BODY = {"sma_km": 26560.0, "ecc": 0.72, "inc_deg": 63.4, "raan_deg": 30.0, "aop_deg": 270.0, "ta_deg": 5.0,
        "model": "j2", "method": "RKF78", "num_points": 200, "duration_s": 21600.0,
        "epoch": "2026-01-01T00:00:00Z", "steering": "covariance", "fidelity": "ecr_mf"}


class TestInnovationsAPI(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.server = create_server(port=0)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.base = f"http://127.0.0.1:{cls.server.server_address[1]}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def post(self, body):
        req = urllib.request.Request(self.base + "/api/propagate", json.dumps(body).encode(),
                                     {"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=300) as resp:
            return json.loads(resp.read())

    def test_innovation_reports_come_from_the_run(self):
        first, second = self.post(BODY), self.post(BODY)
        suite_a, suite_b = first["innovations_suite"], second["innovations_suite"]
        self.assertEqual(suite_a["covariance_steered_stepping"], suite_b["covariance_steered_stepping"])
        self.assertEqual(suite_a["ecr_mf"], suite_b["ecr_mf"])

        r, v = keplerian_to_cartesian(26560e3, 0.72, *np.radians([63.4, 30.0, 270.0, 5.0]))
        own = ThirdReviewEngine(np.concatenate([r, v]), epoch=BODY["epoch"]).propagate(
            (0.0, BODY["duration_s"]), num_points=200, model="j2", method="RKF78", rtol=1e-10, atol=1e-10,
            steering="covariance", fidelity="ecr_mf")
        steering = suite_a["covariance_steered_stepping"]
        self.assertEqual(steering["accepted_steps"], len(own["steps"]["t_s"]) - 1)
        self.assertEqual(steering["limited_steps"], sum(own["steps"]["limited"]))
        self.assertEqual(len(suite_a["ecr_mf"]["switches"]), len(own["ecr_mf"]["switches"]))

    def test_steered_endpoint_rejects_parameters_that_cannot_finish(self):
        """eta <= 0 would cap every step at zero (a request that never returns); orbits that
        hit the Earth or are not closed have no period to propagate over."""
        for query in ("eta=0", "eta=-1", "eta=nan", "ecc=1.2", "sma=3000", "sma=26560&ecc=0.9"):
            with self.subTest(query=query):
                with self.assertRaises(urllib.error.HTTPError) as ctx:
                    urllib.request.urlopen(f"{self.base}/api/covariance/steered?{query}", timeout=30)
                self.assertEqual(ctx.exception.code, 400)

    def test_plain_runs_claim_no_steering(self):
        plain = self.post({k: v for k, v in BODY.items() if k not in ("steering", "fidelity")})
        suite = plain["innovations_suite"]
        self.assertIsNone(suite["covariance_steered_stepping"])
        self.assertIsNone(suite["ecr_mf"])


if __name__ == "__main__":
    unittest.main()
