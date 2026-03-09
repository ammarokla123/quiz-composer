import os
import random

import quizcomp.group
import quizcomp.question.base
import quizcomp.quiz
import tests.base

QUESTIONS_DIR = os.path.join(tests.base.TESTS_DIR, 'questions', 'good')

class GroupVariantTest(tests.base.BaseTest):
    """
    Test group question selection and variant creation.
    """

    def _load_question(self, name):
        path = os.path.join(QUESTIONS_DIR, name, 'question.json')
        return quizcomp.question.base.Question.from_path(path)

    def _make_group(self, name, questions, pick_count = None, **kwargs):
        if (pick_count is None):
            pick_count = len(questions)

        return quizcomp.group.Group(
            name = name,
            pick_count = pick_count,
            questions = questions,
            **kwargs,
        )

    def test_variant_seed_reproducibility(self):
        quiz_path = os.path.join(tests.base.GOOD_QUIZZES_DIR, 'multi-question-group', 'quiz.json')

        quiz_a = quizcomp.quiz.Quiz.from_path(quiz_path)
        variant_a = quiz_a.create_variant(seed = 42)

        quiz_b = quizcomp.quiz.Quiz.from_path(quiz_path)
        variant_b = quiz_b.create_variant(seed = 42)

        types_a = [q.question_type for q in variant_a.questions]
        types_b = [q.question_type for q in variant_b.questions]

        self.assertEqual(types_a, types_b)

    def test_variant_different_seeds(self):
        quiz_path = os.path.join(tests.base.GOOD_QUIZZES_DIR, 'multi-question-group', 'quiz.json')

        seen_orderings = set()
        for seed_value in range(50):
            quiz = quizcomp.quiz.Quiz.from_path(quiz_path)
            variant = quiz.create_variant(seed = seed_value)
            ordering = tuple(q.question_type for q in variant.questions)
            seen_orderings.add(ordering)

        self.assertGreater(len(seen_orderings), 1)

    def test_pick_count_subset(self):
        quiz_path = os.path.join(tests.base.GOOD_QUIZZES_DIR, 'multi-question-group', 'quiz.json')
        quiz = quizcomp.quiz.Quiz.from_path(quiz_path)
        variant = quiz.create_variant(seed = 42)

        self.assertEqual(len(variant.questions), 2)

    def test_pick_with_replacement(self):
        questions = [self._load_question('mcq-basic'), self._load_question('tf-true')]
        group = self._make_group('Replacement Group', questions, pick_count = 2)

        rng = random.Random(42)
        chosen = group.choose_questions(rng = rng, with_replacement = True)

        self.assertEqual(len(chosen), 2)

    def test_pick_without_replacement_exhausts_pool(self):
        questions = [self._load_question('mcq-basic'), self._load_question('tf-true')]
        group = self._make_group('No-Replacement Group', questions, pick_count = 2,
                pick_with_replacement = False)

        rng = random.Random(42)
        chosen = group.choose_questions(rng = rng, with_replacement = False)

        types = sorted([q.question_type for q in chosen])
        self.assertEqual(types, ['multiple_choice', 'true_false'])

    def test_multi_pick_renames_questions(self):
        questions = [
            self._load_question('mcq-basic'),
            self._load_question('tf-true'),
            self._load_question('sa-basic'),
        ]
        group = self._make_group('RenameGroup', questions, pick_count = 3)

        rng = random.Random(42)
        chosen = group.choose_questions(rng = rng)

        for i in range(len(chosen)):
            expected_name = "RenameGroup - %d" % (i + 1)
            self.assertEqual(chosen[i].name, expected_name)

    def test_single_pick_no_rename_suffix(self):
        questions = [self._load_question('mcq-basic'), self._load_question('tf-true')]
        group = self._make_group('SinglePick', questions, pick_count = 1)

        rng = random.Random(42)
        chosen = group.choose_questions(rng = rng)

        self.assertEqual(len(chosen), 1)
        self.assertNotIn(' - ', chosen[0].name)

    def test_hints_inherited_from_group(self):
        questions = [
            self._load_question('mcq-basic'),
            self._load_question('tf-true'),
            self._load_question('sa-basic'),
        ]
        group = self._make_group('HintGroup', questions, pick_count = 3,
                hints = {'pagebreak_before': True})

        rng = random.Random(42)
        chosen = group.choose_questions(rng = rng)

        for q in chosen:
            self.assertIn('pagebreak_before', q.hints)
            self.assertTrue(q.hints['pagebreak_before'])

    def test_hints_first_only_on_first_question(self):
        questions = [
            self._load_question('mcq-basic'),
            self._load_question('tf-true'),
            self._load_question('sa-basic'),
        ]
        group = self._make_group('HintFirstGroup', questions, pick_count = 3,
                hints_first = {'first_only': True})

        rng = random.Random(42)
        chosen = group.choose_questions(rng = rng)

        self.assertIn('first_only', chosen[0].hints)
        for q in chosen[1:]:
            self.assertNotIn('first_only', q.hints)

    def test_hints_last_only_on_last_question(self):
        questions = [
            self._load_question('mcq-basic'),
            self._load_question('tf-true'),
            self._load_question('sa-basic'),
        ]
        group = self._make_group('HintLastGroup', questions, pick_count = 3,
                hints_last = {'last_only': True})

        rng = random.Random(42)
        chosen = group.choose_questions(rng = rng)

        self.assertIn('last_only', chosen[-1].hints)
        for q in chosen[:-1]:
            self.assertNotIn('last_only', q.hints)

    def test_hints_first_and_last_combined(self):
        questions = [
            self._load_question('mcq-basic'),
            self._load_question('tf-true'),
            self._load_question('sa-basic'),
        ]
        group = self._make_group('CombinedHints', questions, pick_count = 3,
                hints = {'base': True},
                hints_first = {'first_marker': True},
                hints_last = {'last_marker': True})

        rng = random.Random(42)
        chosen = group.choose_questions(rng = rng)

        # All should have base hint.
        for q in chosen:
            self.assertIn('base', q.hints)

        # First has first_marker, not last_marker.
        self.assertIn('first_marker', chosen[0].hints)
        self.assertNotIn('last_marker', chosen[0].hints)

        # Middle has neither.
        self.assertNotIn('first_marker', chosen[1].hints)
        self.assertNotIn('last_marker', chosen[1].hints)

        # Last has last_marker, not first_marker.
        self.assertIn('last_marker', chosen[-1].hints)
        self.assertNotIn('first_marker', chosen[-1].hints)

    def test_multi_group_total_points(self):
        quiz_path = os.path.join(tests.base.GOOD_QUIZZES_DIR, 'multi-question-group', 'quiz.json')
        quiz = quizcomp.quiz.Quiz.from_path(quiz_path)

        # pick_count=2, points=10 (default) → 20 total
        self.assertEqual(quiz.total_points(), 20)

    def test_variant_preserves_total_points(self):
        quiz_path = os.path.join(tests.base.GOOD_QUIZZES_DIR, 'multi-question-group', 'quiz.json')
        quiz = quizcomp.quiz.Quiz.from_path(quiz_path)
        variant = quiz.create_variant(seed = 42)

        self.assertEqual(variant.total_points(), quiz.total_points())

    def test_chosen_questions_are_copies(self):
        questions = [self._load_question('mcq-basic')]
        group = self._make_group('CopyGroup', questions, pick_count = 1)

        rng = random.Random(42)
        chosen = group.choose_questions(rng = rng)

        original_prompt = group.questions[0].prompt
        chosen[0].prompt = 'MODIFIED'

        self.assertNotEqual(group.questions[0].prompt, 'MODIFIED')
        self.assertEqual(group.questions[0].prompt, original_prompt)
