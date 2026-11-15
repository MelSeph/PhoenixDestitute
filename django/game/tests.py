from django.test import TestCase
from django.urls import reverse

class HomePageTests(TestCase):
    def test_game_page_loads(self):
        response = self.client.get(reverse("game-home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Phoenix Destitute")
