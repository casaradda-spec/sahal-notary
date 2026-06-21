from django.contrib.auth import get_user_model
from django.test import TestCase

from portal.utils import generate_username, slugify_ascii

User = get_user_model()


class SlugifyAsciiTests(TestCase):
    def test_basic_two_word_name(self):
        self.assertEqual(slugify_ascii('Farhan.Axmed'), 'farhan.axmed')

    def test_strips_non_alphanumeric_and_lowercases(self):
        self.assertEqual(slugify_ascii("Ka'ase Nuur"), 'ka.ase.nuur')

    def test_empty_input_falls_back_to_user(self):
        self.assertEqual(slugify_ascii(''), 'user')


class GenerateUsernameTests(TestCase):
    def test_two_word_name_uses_first_dot_last(self):
        self.assertEqual(generate_username(User, 'Farhan Axmed'), 'farhan.axmed')

    def test_single_word_name(self):
        self.assertEqual(generate_username(User, 'Madonna'), 'madonna')

    def test_collision_appends_incrementing_suffix(self):
        User.objects.create_user(username='farhan.axmed', password='123')
        self.assertEqual(generate_username(User, 'Farhan Axmed'), 'farhan.axmed2')

        User.objects.create_user(username='farhan.axmed2', password='123')
        self.assertEqual(generate_username(User, 'Farhan Axmed'), 'farhan.axmed3')

    def test_many_word_name_uses_first_and_last_only(self):
        self.assertEqual(generate_username(User, 'Maxamed Daahir Axmed'), 'maxamed.axmed')
