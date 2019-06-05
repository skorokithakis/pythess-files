from unittest import mock

from django.core.checks import Error, Warning as DjangoWarning
from django.db import connection, models
from django.db.models.fields.related import ForeignObject
from django.test.testcases import SimpleTestCase
from django.test.utils import isolate_apps, override_settings


@isolate_apps('invalid_models_tests')
class RelativeFieldTests(SimpleTestCase):

    def test_valid_foreign_key_without_accessor(self):
        class Target(models.Model):
            # There would be a clash if Model.field installed an accessor.
            model = models.IntegerField()

        class Model(models.Model):
            field = models.ForeignKey(Target, models.CASCADE, related_name='+')

        field = Model._meta.get_field('field')
        self.assertEqual(field.check(), [])

    def test_foreign_key_to_missing_model(self):
        # Model names are resolved when a model is being created, so we cannot
        # test relative fields in isolation and we need to attach them to a
        # model.
        class Model(models.Model):
            foreign_key = models.ForeignKey('Rel1', models.CASCADE)

        field = Model._meta.get_field('foreign_key')
        self.assertEqual(field.check(), [
            Error(
                "Field defines a relation with model 'Rel1', "
                "which is either not installed, or is abstract.",
                obj=field,
                id='fields.E300',
            ),
        ])

    @isolate_apps('invalid_models_tests')
    def test_foreign_key_to_isolate_apps_model(self):
        """
        #25723 - Referenced model registration lookup should be run against the
        field's model registry.
        """
        class OtherModel(models.Model):
            pass

        class Model(models.Model):
            foreign_key = models.ForeignKey('OtherModel', models.CASCADE)

        field = Model._meta.get_field('foreign_key')
        self.assertEqual(field.check(from_model=Model), [])

    def test_many_to_many_to_missing_model(self):
        class Model(models.Model):
            m2m = models.ManyToManyField("Rel2")

        field = Model._meta.get_field('m2m')
        self.assertEqual(field.check(from_model=Model), [
            Error(
                "Field defines a relation with model 'Rel2', "
                "which is either not installed, or is abstract.",
                obj=field,
                id='fields.E300',
            ),
        ])

    @isolate_apps('invalid_models_tests')
    def test_many_to_many_to_isolate_apps_model(self):
        """
        #25723 - Referenced model registration lookup should be run against the
        field's model registry.
        """
        class OtherModel(models.Model):
            pass

        class Model(models.Model):
            m2m = models.ManyToManyField('OtherModel')

        field = Model._meta.get_field('m2m')
        self.assertEqual(field.check(from_model=Model), [])

    def test_many_to_many_with_limit_choices_auto_created_no_warning(self):
        class Model(models.Model):
            name = models.CharField(max_length=20)

        class ModelM2M(models.Model):
            m2m = models.ManyToManyField(Model, limit_choices_to={'name': 'test_name'})

        self.assertEqual(ModelM2M.check(), [])

    def test_many_to_many_with_useless_options(self):
        class Model(models.Model):
            name = models.CharField(max_length=20)

        class ModelM2M(models.Model):
            m2m = models.ManyToManyField(
                Model,
                null=True,
                validators=[lambda x: x],
                limit_choices_to={'name': 'test_name'},
                through='ThroughModel',
                through_fields=('modelm2m', 'model'),
            )

        class ThroughModel(models.Model):
            model = models.ForeignKey('Model', models.CASCADE)
            modelm2m = models.ForeignKey('ModelM2M', models.CASCADE)

        field = ModelM2M._meta.get_field('m2m')
        self.assertEqual(ModelM2M.check(), [
            DjangoWarning(
                'null has no effect on ManyToManyField.',
                obj=field,
                id='fields.W340',
            ),
            DjangoWarning(
                'ManyToManyField does not support validators.',
                obj=field,
                id='fields.W341',
            ),
            DjangoWarning(
                'limit_choices_to has no effect on ManyToManyField '
                'with a through model.',
                obj=field,
                id='fields.W343',
            ),
        ])

    def test_ambiguous_relationship_model(self):

        class Person(models.Model):
            pass

        class Group(models.Model):
            field = models.ManyToManyField('Person', through="AmbiguousRelationship", related_name='tertiary')

        class AmbiguousRelationship(models.Model):
            # Too much foreign keys to Person.
            first_person = models.ForeignKey(Person, models.CASCADE, related_name="first")
            second_person = models.ForeignKey(Person, models.CASCADE, related_name="second")
            second_model = models.ForeignKey(Group, models.CASCADE)

        field = Group._meta.get_field('field')
        self.assertEqual(field.check(from_model=Group), [
            Error(
                "The model is used as an intermediate model by "
                "'invalid_models_tests.Group.field', but it has more than one "
                "foreign key to 'Person', which is ambiguous. You must specify "
                "which foreign key Django should use via the through_fields "
                "keyword argument.",
                hint=(
                    'If you want to create a recursive relationship, use '
                    'ForeignKey("self", symmetrical=False, through="AmbiguousRelationship").'
                ),
                obj=field,
                id='fields.E335',
            ),
        ])

    def test_relationship_model_with_foreign_key_to_wrong_model(self):
        class WrongModel(models.Model):
            pass

        class Person(models.Model):
            pass

        class Group(models.Model):
            members = models.ManyToManyField('Person', through="InvalidRelationship")

        class InvalidRelationship(models.Model):
            person = models.ForeignKey(Person, models.CASCADE)
            wrong_foreign_key = models.ForeignKey(WrongModel, models.CASCADE)
            # The last foreign key should point to Group model.

        field = Group._meta.get_field('members')
        self.assertEqual(field.check(from_model=Group), [
            Error(
                "The model is used as an intermediate model by "
                "'invalid_models_tests.Group.members', but it does not "
                "have a foreign key to 'Group' or 'Person'.",
                obj=InvalidRelationship,
                id='fields.E336',
            ),
        ])

    def test_relationship_model_missing_foreign_key(self):
        class Person(models.Model):
            pass

        class Group(models.Model):
            members = models.ManyToManyField('Person', through="InvalidRelationship")

        class InvalidRelationship(models.Model):
            group = models.ForeignKey(Group, models.CASCADE)
            # No foreign key to Person

        field = Group._meta.get_field('members')
        self.assertEqual(field.check(from_model=Group), [
            Error(
                "The model is used as an intermediate model by "
                "'invalid_models_tests.Group.members', but it does not have "
                "a foreign key to 'Group' or 'Person'.",
                obj=InvalidRelationship,
                id='fields.E336',
            ),
        ])

    def test_missing_relationship_model(self):
        class Person(models.Model):
            pass

        class Group(models.Model):
            members = models.ManyToManyField('Person', through="MissingM2MModel")

        field = Group._meta.get_field('members')
        self.assertEqual(field.check(from_model=Group), [
            Error(
                "Field specifies a many-to-many relation through model "
                "'MissingM2MModel', which has not been installed.",
                obj=field,
                id='fields.E331',
            ),
        ])

    def test_missing_relationship_model_on_model_check(self):
        class Person(models.Model):
            pass

        class Group(models.Model):
            members = models.ManyToManyField('Person', through='MissingM2MModel')

        self.assertEqual(Group.check(), [
            Error(
                "Field specifies a many-to-many relation through model "
                "'MissingM2MModel', which has not been installed.",
                obj=Group._meta.get_field('members'),
                id='fields.E331',
            ),
        ])

    @isolate_apps('invalid_models_tests')
    def test_many_to_many_through_isolate_apps_model(self):
        """
        #25723 - Through model registration lookup should be run against the
        field's model registry.
        """
        class GroupMember(models.Model):
            person = models.ForeignKey('Person', models.CASCADE)
            group = models.ForeignKey('Group', models.CASCADE)

        class Person(models.Model):
            pass

        class Group(models.Model):
            members = models.ManyToManyField('Person', through='GroupMember')

        field = Group._meta.get_field('members')
        self.assertEqual(field.check(from_model=Group), [])

    def test_symmetrical_self_referential_field(self):
        class Person(models.Model):
            # Implicit symmetrical=False.
            friends = models.ManyToManyField('self', through="Relationship")

        class Relationship(models.Model):
            first = models.ForeignKey(Person, models.CASCADE, related_name="rel_from_set")
            second = models.ForeignKey(Person, models.CASCADE, related_name="rel_to_set")

        field = Person._meta.get_field('friends')
        self.assertEqual(field.check(from_model=Person), [
            Error(
                'Many-to-many fields with intermediate tables must not be symmetrical.',
                obj=field,
                id='fields.E332',
            ),
        ])

    def test_too_many_foreign_keys_in_self_referential_model(self):
        class Person(models.Model):
            friends = models.ManyToManyField('self', through="InvalidRelationship", symmetrical=False)

        class InvalidRelationship(models.Model):
            first = models.ForeignKey(Person, models.CASCADE, related_name="rel_from_set_2")
            second = models.ForeignKey(Person, models.CASCADE, related_name="rel_to_set_2")
            third = models.ForeignKey(Person, models.CASCADE, related_name="too_many_by_far")

        field = Person._meta.get_field('friends')
        self.assertEqual(field.check(from_model=Person), [
            Error(
                "The model is used as an intermediate model by "
                "'invalid_models_tests.Person.friends', but it has more than two "
                "foreign keys to 'Person', which is ambiguous. You must specify "
                "which two foreign keys Django should use via the through_fields "
                "keyword argument.",
                hint='Use through_fields to specify which two foreign keys Django should use.',
                obj=InvalidRelationship,
                id='fields.E333',
            ),
        ])

    def test_symmetric_self_reference_with_intermediate_table(self):
        class Person(models.Model):
            # Explicit symmetrical=True.
            friends = models.ManyToManyField('self', through="Relationship", symmetrical=True)

        class Relationship(models.Model):
            first = models.ForeignKey(Person, models.CASCADE, related_name="rel_from_set")
            second = models.ForeignKey(Person, models.CASCADE, related_name="rel_to_set")

        field = Person._meta.get_field('friends')
        self.assertEqual(field.check(from_model=Person), [
            Error(
                'Many-to-many fields with intermediate tables must not be symmetrical.',
                obj=field,
                id='fields.E332',
            ),
        ])

    def test_symmetric_self_reference_with_intermediate_table_and_through_fields(self):
        """
        Using through_fields in a m2m with an intermediate model shouldn't
        mask its incompatibility with symmetry.
        """
        class Person(models.Model):
            # Explicit symmetrical=True.
            friends = models.ManyToManyField(
                'self',
                symmetrical=True,
                through="Relationship",
                through_fields=('first', 'second'),
            )

        class Relationship(models.Model):
            first = models.ForeignKey(Person, models.CASCADE, related_name="rel_from_set")
            second = models.ForeignKey(Person, models.CASCADE, related_name="rel_to_set")
            referee = models.ForeignKey(Person, models.CASCADE, related_name="referred")

        field = Person._meta.get_field('friends')
        self.assertEqual(field.check(from_model=Person), [
            Error(
                'Many-to-many fields with intermediate tables must not be symmetrical.',
                obj=field,
                id='fields.E332',
            ),
        ])

    def test_foreign_key_to_abstract_model(self):
        class AbstractModel(models.Model):
            class Meta:
                abstract = True

        class Model(models.Model):
            rel_string_foreign_key = models.ForeignKey('AbstractModel', models.CASCADE)
            rel_class_foreign_key = models.ForeignKey(AbstractModel, models.CASCADE)

        fields = [
            Model._meta.get_field('rel_string_foreign_key'),
            Model._meta.get_field('rel_class_foreign_key'),
        ]
        expected_error = Error(
            "Field defines a relation with model 'AbstractModel', "
            "which is either not installed, or is abstract.",
            id='fields.E300',
        )
        for field in fields:
            expected_error.obj = field
            self.assertEqual(field.check(), [expected_error])

    def test_m2m_to_abstract_model(self):
        class AbstractModel(models.Model):
            class Meta:
                abstract = True

        class Model(models.Model):
            rel_string_m2m = models.ManyToManyField('AbstractModel')
            rel_class_m2m = models.ManyToManyField(AbstractModel)

        fields = [
            Model._meta.get_field('rel_string_m2m'),
            Model._meta.get_field('rel_class_m2m'),
        ]
        expected_error = Error(
            "Field defines a relation with model 'AbstractModel', "
            "which is either not installed, or is abstract.",
            id='fields.E300',
        )
        for field in fields:
            expected_error.obj = field
            self.assertEqual(field.check(from_model=Model), [expected_error])

    def test_unique_m2m(self):
        class Person(models.Model):
            name = models.CharField(max_length=5)

        class Group(models.Model):
            members = models.ManyToManyField('Person', unique=True)

        field = Group._meta.get_field('members')
        self.assertEqual(field.check(from_model=Group), [
            Error(
                'ManyToManyFields cannot be unique.',
                obj=field,
                id='fields.E330',
            ),
        ])

    def test_foreign_key_to_non_unique_field(self):
        class Target(models.Model):
            bad = models.IntegerField()  # No unique=True

        class Model(models.Model):
            foreign_key = models.ForeignKey('Target', models.CASCADE, to_field='bad')

        field = Model._meta.get_field('foreign_key')
        self.assertEqual(field.check(), [
            Error(
                "'Target.bad' must set unique=True because it is referenced by a foreign key.",
                obj=field,
                id='fields.E311',
            ),
        ])

    def test_foreign_key_to_non_unique_field_under_explicit_model(self):
        class Target(models.Model):
            bad = models.IntegerField()

        class Model(models.Model):
            field = models.ForeignKey(Target, models.CASCADE, to_field='bad')

        field = Model._meta.get_field('field')
        self.assertEqual(field.check(), [
            Error(
                "'Target.bad' must set unique=True because it is referenced by a foreign key.",
                obj=field,
                id='fields.E311',
            ),
        ])

    def test_foreign_object_to_non_unique_fields(self):
        class Person(models.Model):
            # Note that both fields are not unique.
            country_id = models.IntegerField()
            city_id = models.IntegerField()

        class MMembership(models.Model):
            person_country_id = models.IntegerField()
            person_city_id = models.IntegerField()

            person = models.ForeignObject(
                Person,
                on_delete=models.CASCADE,
                from_fields=['person_country_id', 'person_city_id'],
                to_fields=['country_id', 'city_id'],
            )

        field = MMembership._meta.get_field('person')
        self.assertEqual(field.check(), [
            Error(
                "No subset of the fields 'country_id', 'city_id' on model 'Person' is unique.",
                hint=(
                    "Add unique=True on any of those fields or add at least "
                    "a subset of them to a unique_together constraint."
                ),
                obj=field,
                id='fields.E310',
            )
        ])

    def test_on_delete_set_null_on_non_nullable_field(self):
        class Person(models.Model):
            pass

        class Model(models.Model):
            foreign_key = models.ForeignKey('Person', models.SET_NULL)

        field = Model._meta.get_field('foreign_key')
        self.assertEqual(field.check(), [
            Error(
                'Field specifies on_delete=SET_NULL, but cannot be null.',
                hint='Set null=True argument on the field, or change the on_delete rule.',
                obj=field,
                id='fields.E320',
            ),
        ])

    def test_on_delete_set_default_without_default_value(self):
        class Person(models.Model):
            pass

        class Model(models.Model):
            foreign_key = models.ForeignKey('Person', models.SET_DEFAULT)

        field = Model._meta.get_field('foreign_key')
        self.assertEqual(field.check(), [
            Error(
                'Field specifies on_delete=SET_DEFAULT, but has no default value.',
                hint='Set a default value, or change the on_delete rule.',
                obj=field,
                id='fields.E321',
            ),
        ])

    def test_nullable_primary_key(self):
        class Model(models.Model):
            field = models.IntegerField(primary_key=True, null=True)

        field = Model._meta.get_field('field')
        with mock.patch.object(connection.features, 'interprets_empty_strings_as_nulls', False):
            results = field.check()
        self.assertEqual(results, [
            Error(
                'Primary keys must not have null=True.',
                hint='Set null=False on the field, or remove primary_key=True argument.',
                obj=field,
                id='fields.E007',
            ),
        ])

    def test_not_swapped_model(self):
        class SwappableModel(models.Model):
            # A model that can be, but isn't swapped out. References to this
            # model should *not* raise any validation error.
            class Meta:
                swappable = 'TEST_SWAPPABLE_MODEL'

        class Model(models.Model):
            explicit_fk = models.ForeignKey(
                SwappableModel,
                models.CASCADE,
                related_name='explicit_fk',
            )
            implicit_fk = models.ForeignKey(
                'invalid_models_tests.SwappableModel',
                models.CASCADE,
                related_name='implicit_fk',
            )
            explicit_m2m = models.ManyToManyField(SwappableModel, related_name='explicit_m2m')
            implicit_m2m = models.ManyToManyField(
                'invalid_models_tests.SwappableModel',
                related_name='implicit_m2m',
            )

        explicit_fk = Model._meta.get_field('explicit_fk')
        self.assertEqual(explicit_fk.check(), [])

        implicit_fk = Model._meta.get_field('implicit_fk')
        self.assertEqual(implicit_fk.check(), [])

        explicit_m2m = Model._meta.get_field('explicit_m2m')
        self.assertEqual(explicit_m2m.check(from_model=Model), [])

        implicit_m2m = Model._meta.get_field('implicit_m2m')
        self.assertEqual(implicit_m2m.check(from_model=Model), [])

    @override_settings(TEST_SWAPPED_MODEL='invalid_models_tests.Replacement')
    def test_referencing_to_swapped_model(self):
        class Replacement(models.Model):
            pass

        class SwappedModel(models.Model):
            class Meta:
                swappable = 'TEST_SWAPPED_MODEL'

        class Model(models.Model):
            explicit_fk = models.ForeignKey(
                SwappedModel,
                models.CASCADE,
                related_name='explicit_fk',
            )
            implicit_fk = models.ForeignKey(
                'invalid_models_tests.SwappedModel',
                models.CASCADE,
                related_name='implicit_fk',
            )
            explicit_m2m = models.ManyToManyField(SwappedModel, related_name='explicit_m2m')
            implicit_m2m = models.ManyToManyField(
                'invalid_models_tests.SwappedModel',
                related_name='implicit_m2m',
            )

        fields = [
            Model._meta.get_field('explicit_fk'),
            Model._meta.get_field('implicit_fk'),
            Model._meta.get_field('explicit_m2m'),
            Model._meta.get_field('implicit_m2m'),
        ]

        expected_error = Error(
            ("Field defines a relation with the model "
             "'invalid_models_tests.SwappedModel', which has been swapped out."),
            hint="Update the relation to point at 'settings.TEST_SWAPPED_MODEL'.",
            id='fields.E301',
        )

        for field in fields:
            expected_error.obj = field
            self.assertEqual(field.check(from_model=Model), [expected_error])

    def test_related_field_has_invalid_related_name(self):
        digit = 0
        illegal_non_alphanumeric = '!'
        whitespace = '\t'

        invalid_related_names = [
            '%s_begins_with_digit' % digit,
            '%s_begins_with_illegal_non_alphanumeric' % illegal_non_alphanumeric,
            '%s_begins_with_whitespace' % whitespace,
            'contains_%s_illegal_non_alphanumeric' % illegal_non_alphanumeric,
            'contains_%s_whitespace' % whitespace,
            'ends_with_with_illegal_non_alphanumeric_%s' % illegal_non_alphanumeric,
            'ends_with_whitespace_%s' % whitespace,
            'with',  # a Python keyword
            'related_name\n',
            '',
            '，',  # non-ASCII
        ]

        class Parent(models.Model):
            pass

        for invalid_related_name in invalid_related_names:
            Child = type('Child%s' % invalid_related_name, (models.Model,), {
                'parent': models.ForeignKey('Parent', models.CASCADE, related_name=invalid_related_name),
                '__module__': Parent.__module__,
            })

            field = Child._meta.get_field('parent')
            self.assertEqual(Child.check(), [
                Error(
                    "The name '%s' is invalid related_name for field Child%s.parent"
                    % (invalid_related_name, invalid_related_name),
                    hint="Related name must be a valid Python identifier or end with a '+'",
                    obj=field,
                    id='fields.E306',
                ),
            ])

    def test_related_field_has_valid_related_name(self):
        lowercase = 'a'
        uppercase = 'A'
        digit = 0

        related_names = [
            '%s_starts_with_lowercase' % lowercase,
            '%s_tarts_with_uppercase' % uppercase,
            '_starts_with_underscore',
            'contains_%s_digit' % digit,
            'ends_with_plus+',
            '_+',
            '+',
            '試',
            '試驗+',
        ]

        class Parent(models.Model):
            pass

        for related_name in related_names:
            Child = type('Child%s' % related_name, (models.Model,), {
                'parent': models.ForeignKey('Parent', models.CASCADE, related_name=related_name),
                '__module__': Parent.__module__,
            })
            self.assertEqual(Child.check(), [])

    def test_to_fields_exist(self):
        class Parent(models.Model):
            pass

        class Child(models.Model):
            a = models.PositiveIntegerField()
            b = models.PositiveIntegerField()
            parent = ForeignObject(
                Parent,
                on_delete=models.SET_NULL,
                from_fields=('a', 'b'),
                to_fields=('a', 'b'),
            )

        field = Child._meta.get_field('parent')
        self.assertEqual(field.check(), [
            Error(
                "The to_field 'a' doesn't exist on the related model 'invalid_models_tests.Parent'.",
                obj=field,
                id='fields.E312',
            ),
            Error(
                "The to_field 'b' doesn't exist on the related model 'invalid_models_tests.Parent'.",
                obj=field,
                id='fields.E312',
            ),
        ])

    def test_to_fields_not_checked_if_related_model_doesnt_exist(self):
        class Child(models.Model):
            a = models.PositiveIntegerField()
            b = models.PositiveIntegerField()
            parent = ForeignObject(
                'invalid_models_tests.Parent',
                on_delete=models.SET_NULL,
                from_fields=('a', 'b'),
                to_fields=('a', 'b'),
            )

        field = Child._meta.get_field('parent')
        self.assertEqual(field.check(), [
            Error(
                "Field defines a relation with model 'invalid_models_tests.Parent', "
                "which is either not installed, or is abstract.",
                id='fields.E300',
                obj=field,
            ),
        ])

    def test_invalid_related_query_name(self):
        class Target(models.Model):
            pass

        class Model(models.Model):
            first = models.ForeignKey(Target, models.CASCADE, related_name='contains__double')
            second = models.ForeignKey(Target, models.CASCADE, related_query_name='ends_underscore_')

        self.assertEqual(Model.check(), [
            Error(
                "Reverse query name 'contains__double' must not contain '__'.",
                hint=("Add or change a related_name or related_query_name "
                      "argument for this field."),
                obj=Model._meta.get_field('first'),
                id='fields.E309',
            ),
            Error(
                "Reverse query name 'ends_underscore_' must not end with an "
                "underscore.",
                hint=("Add or change a related_name or related_query_name "
                      "argument for this field."),
                obj=Model._meta.get_field('second'),
                id='fields.E308',
            ),
        ])


@isolate_apps('invalid_models_tests')
class AccessorClashTests(SimpleTestCase):

    def test_fk_to_integer(self):
        self._test_accessor_clash(
            target=models.IntegerField(),
            relative=models.ForeignKey('Target', models.CASCADE))

    def test_fk_to_fk(self):
        self._test_accessor_clash(
            target=models.ForeignKey('Another', models.CASCADE),
            relative=models.ForeignKey('Target', models.CASCADE))

    def test_fk_to_m2m(self):
        self._test_accessor_clash(
            target=models.ManyToManyField('Another'),
            relative=models.ForeignKey('Target', models.CASCADE))

    def test_m2m_to_integer(self):
        self._test_accessor_clash(
            target=models.IntegerField(),
            relative=models.ManyToManyField('Target'))

    def test_m2m_to_fk(self):
        self._test_accessor_clash(
            target=models.ForeignKey('Another', models.CASCADE),
            relative=models.ManyToManyField('Target'))

    def test_m2m_to_m2m(self):
        self._test_accessor_clash(
            target=models.ManyToManyField('Another'),
            relative=models.ManyToManyField('Target'))

    def _test_accessor_clash(self, target, relative):
        class Another(models.Model):
            pass

        class Target(models.Model):
            model_set = target

        class Model(models.Model):
            rel = relative

        self.assertEqual(Model.check(), [
            Error(
                "Reverse accessor for 'Model.rel' clashes with field name 'Target.model_set'.",
                hint=("Rename field 'Target.model_set', or add/change "
                      "a related_name argument to the definition "
                      "for field 'Model.rel'."),
                obj=Model._meta.get_field('rel'),
                id='fields.E302',
            ),
        ])

    def test_clash_between_accessors(self):
        class Target(models.Model):
            pass

        class Model(models.Model):
            foreign = models.ForeignKey(Target, models.CASCADE)
            m2m = models.ManyToManyField(Target)

        self.assertEqual(Model.check(), [
            Error(
                "Reverse accessor for 'Model.foreign' clashes with reverse accessor for 'Model.m2m'.",
                hint=(
                    "Add or change a related_name argument to the definition "
                    "for 'Model.foreign' or 'Model.m2m'."
                ),
                obj=Model._meta.get_field('foreign'),
                id='fields.E304',
            ),
            Error(
                "Reverse accessor for 'Model.m2m' clashes with reverse accessor for 'Model.foreign'.",
                hint=(
                    "Add or change a related_name argument to the definition "
                    "for 'Model.m2m' or 'Model.foreign'."
                ),
                obj=Model._meta.get_field('m2m'),
                id='fields.E304',
            ),
        ])

    def test_m2m_to_m2m_with_inheritance(self):
        """ Ref #22047. """

        class Target(models.Model):
            pass

        class Model(models.Model):
            children = models.ManyToManyField('Child', related_name="m2m_clash", related_query_name="no_clash")

        class Parent(models.Model):
            m2m_clash = models.ManyToManyField('Target')

        class Child(Parent):
            pass

        self.assertEqual(Model.check(), [
            Error(
                "Reverse accessor for 'Model.children' clashes with field name 'Child.m2m_clash'.",
                hint=(
                    "Rename field 'Child.m2m_clash', or add/change a related_name "
                    "argument to the definition for field 'Model.children'."
                ),
                obj=Model._meta.get_field('children'),
                id='fields.E302',
            )
        ])

    def test_no_clash_for_hidden_related_name(self):
        class Stub(models.Model):
            pass

        class ManyToManyRel(models.Model):
            thing1 = models.ManyToManyField(Stub, related_name='+')
            thing2 = models.ManyToManyField(Stub, related_name='+')

        class FKRel(models.Model):
            thing1 = models.ForeignKey(Stub, models.CASCADE, related_name='+')
            thing2 = models.ForeignKey(Stub, models.CASCADE, related_name='+')

        self.assertEqual(ManyToManyRel.check(), [])
        self.assertEqual(FKRel.check(), [])


@isolate_apps('invalid_models_tests')
class ReverseQueryNameClashTests(SimpleTestCase):

    def test_fk_to_integer(self):
        self._test_reverse_query_name_clash(
            target=models.IntegerField(),
            relative=models.ForeignKey('Target', models.CASCADE))

    def test_fk_to_fk(self):
        self._test_reverse_query_name_clash(
            target=models.ForeignKey('Another', models.CASCADE),
            relative=models.ForeignKey('Target', models.CASCADE))

    def test_fk_to_m2m(self):
        self._test_reverse_query_name_clash(
            target=models.ManyToManyField('Another'),
            relative=models.ForeignKey('Target', models.CASCADE))

    def test_m2m_to_integer(self):
        self._test_reverse_query_name_clash(
            target=models.IntegerField(),
            relative=models.ManyToManyField('Target'))

    def test_m2m_to_fk(self):
        self._test_reverse_query_name_clash(
            target=models.ForeignKey('Another', models.CASCADE),
            relative=models.ManyToManyField('Target'))

    def test_m2m_to_m2m(self):
        self._test_reverse_query_name_clash(
            target=models.ManyToManyField('Another'),
            relative=models.ManyToManyField('Target'))

    def _test_reverse_query_name_clash(self, target, relative):
        class Another(models.Model):
            pass

        class Target(models.Model):
            model = target

        class Model(models.Model):
            rel = relative

        self.assertEqual(Model.check(), [
            Error(
                "Reverse query name for 'Model.rel' clashes with field name 'Target.model'.",
                hint=(
                    "Rename field 'Target.model', or add/change a related_name "
                    "argument to the definition for field 'Model.rel'."
                ),
                obj=Model._meta.get_field('rel'),
                id='fields.E303',
            ),
        ])


@isolate_apps('invalid_models_tests')
class ExplicitRelatedNameClashTests(SimpleTestCase):

    def test_fk_to_integer(self):
        self._test_explicit_related_name_clash(
            target=models.IntegerField(),
            relative=models.ForeignKey('Target', models.CASCADE, related_name='clash'))

    def test_fk_to_fk(self):
        self._test_explicit_related_name_clash(
            target=models.ForeignKey('Another', models.CASCADE),
            relative=models.ForeignKey('Target', models.CASCADE, related_name='clash'))

    def test_fk_to_m2m(self):
        self._test_explicit_related_name_clash(
            target=models.ManyToManyField('Another'),
            relative=models.ForeignKey('Target', models.CASCADE, related_name='clash'))

    def test_m2m_to_integer(self):
        self._test_explicit_related_name_clash(
            target=models.IntegerField(),
            relative=models.ManyToManyField('Target', related_name='clash'))

    def test_m2m_to_fk(self):
        self._test_explicit_related_name_clash(
            target=models.ForeignKey('Another', models.CASCADE),
            relative=models.ManyToManyField('Target', related_name='clash'))

    def test_m2m_to_m2m(self):
        self._test_explicit_related_name_clash(
            target=models.ManyToManyField('Another'),
            relative=models.ManyToManyField('Target', related_name='clash'))

    def _test_explicit_related_name_clash(self, target, relative):
        class Another(models.Model):
            pass

        class Target(models.Model):
            clash = target

        class Model(models.Model):
            rel = relative

        self.assertEqual(Model.check(), [
            Error(
                "Reverse accessor for 'Model.rel' clashes with field name 'Target.clash'.",
                hint=(
                    "Rename field 'Target.clash', or add/change a related_name "
                    "argument to the definition for field 'Model.rel'."
                ),
                obj=Model._meta.get_field('rel'),
                id='fields.E302',
            ),
            Error(
                "Reverse query name for 'Model.rel' clashes with field name 'Target.clash'.",
                hint=(
                    "Rename field 'Target.clash', or add/change a related_name "
                    "argument to the definition for field 'Model.rel'."
                ),
                obj=Model._meta.get_field('rel'),
                id='fields.E303',
            ),
        ])


@isolate_apps('invalid_models_tests')
class ExplicitRelatedQueryNameClashTests(SimpleTestCase):

    def test_fk_to_integer(self, related_name=None):
        self._test_explicit_related_query_name_clash(
            target=models.IntegerField(),
            relative=models.ForeignKey(
                'Target',
                models.CASCADE,
                related_name=related_name,
                related_query_name='clash',
            )
        )

    def test_hidden_fk_to_integer(self, related_name=None):
        self.test_fk_to_integer(related_name='+')

    def test_fk_to_fk(self, related_name=None):
        self._test_explicit_related_query_name_clash(
            target=models.ForeignKey('Another', models.CASCADE),
            relative=models.ForeignKey(
                'Target',
                models.CASCADE,
                related_name=related_name,
                related_query_name='clash',
            )
        )

    def test_hidden_fk_to_fk(self):
        self.test_fk_to_fk(related_name='+')

    def test_fk_to_m2m(self, related_name=None):
        self._test_explicit_related_query_name_clash(
            target=models.ManyToManyField('Another'),
            relative=models.ForeignKey(
                'Target',
                models.CASCADE,
                related_name=related_name,
                related_query_name='clash',
            )
        )

    def test_hidden_fk_to_m2m(self):
        self.test_fk_to_m2m(related_name='+')

    def test_m2m_to_integer(self, related_name=None):
        self._test_explicit_related_query_name_clash(
            target=models.IntegerField(),
            relative=models.ManyToManyField('Target', related_name=related_name, related_query_name='clash'))

    def test_hidden_m2m_to_integer(self):
        self.test_m2m_to_integer(related_name='+')

    def test_m2m_to_fk(self, related_name=None):
        self._test_explicit_related_query_name_clash(
            target=models.ForeignKey('Another', models.CASCADE),
            relative=models.ManyToManyField('Target', related_name=related_name, related_query_name='clash'))

    def test_hidden_m2m_to_fk(self):
        self.test_m2m_to_fk(related_name='+')

    def test_m2m_to_m2m(self, related_name=None):
        self._test_explicit_related_query_name_clash(
            target=models.ManyToManyField('Another'),
            relative=models.ManyToManyField(
                'Target',
                related_name=related_name,
                related_query_name='clash',
            )
        )

    def test_hidden_m2m_to_m2m(self):
        self.test_m2m_to_m2m(related_name='+')

    def _test_explicit_related_query_name_clash(self, target, relative):
        class Another(models.Model):
            pass

        class Target(models.Model):
            clash = target

        class Model(models.Model):
            rel = relative

        self.assertEqual(Model.check(), [
            Error(
                "Reverse query name for 'Model.rel' clashes with field name 'Target.clash'.",
                hint=(
                    "Rename field 'Target.clash', or add/change a related_name "
                    "argument to the definition for field 'Model.rel'."
                ),
                obj=Model._meta.get_field('rel'),
                id='fields.E303',
            ),
        ])


@isolate_apps('invalid_models_tests')
class SelfReferentialM2MClashTests(SimpleTestCase):

    def test_clash_between_accessors(self):
        class Model(models.Model):
            first_m2m = models.ManyToManyField('self', symmetrical=False)
            second_m2m = models.ManyToManyField('self', symmetrical=False)

        self.assertEqual(Model.check(), [
            Error(
                "Reverse accessor for 'Model.first_m2m' clashes with reverse accessor for 'Model.second_m2m'.",
                hint=(
                    "Add or change a related_name argument to the definition "
                    "for 'Model.first_m2m' or 'Model.second_m2m'."
                ),
                obj=Model._meta.get_field('first_m2m'),
                id='fields.E304',
            ),
            Error(
                "Reverse accessor for 'Model.second_m2m' clashes with reverse accessor for 'Model.first_m2m'.",
                hint=(
                    "Add or change a related_name argument to the definition "
                    "for 'Model.second_m2m' or 'Model.first_m2m'."
                ),
                obj=Model._meta.get_field('second_m2m'),
                id='fields.E304',
            ),
        ])

    def test_accessor_clash(self):
        class Model(models.Model):
            model_set = models.ManyToManyField("self", symmetrical=False)

        self.assertEqual(Model.check(), [
            Error(
                "Reverse accessor for 'Model.model_set' clashes with field name 'Model.model_set'.",
                hint=(
                    "Rename field 'Model.model_set', or add/change a related_name "
                    "argument to the definition for field 'Model.model_set'."
                ),
                obj=Model._meta.get_field('model_set'),
                id='fields.E302',
            ),
        ])

    def test_reverse_query_name_clash(self):
        class Model(models.Model):
            model = models.ManyToManyField("self", symmetrical=False)

        self.assertEqual(Model.check(), [
            Error(
                "Reverse query name for 'Model.model' clashes with field name 'Model.model'.",
                hint=(
                    "Rename field 'Model.model', or add/change a related_name "
                    "argument to the definition for field 'Model.model'."
                ),
                obj=Model._meta.get_field('model'),
                id='fields.E303',
            ),
        ])

    def test_clash_under_explicit_related_name(self):
        class Model(models.Model):
            clash = models.IntegerField()
            m2m = models.ManyToManyField("self", symmetrical=False, related_name='clash')

        self.assertEqual(Model.check(), [
            Error(
                "Reverse accessor for 'Model.m2m' clashes with field name 'Model.clash'.",
                hint=(
                    "Rename field 'Model.clash', or add/change a related_name "
                    "argument to the definition for field 'Model.m2m'."
                ),
                obj=Model._meta.get_field('m2m'),
                id='fields.E302',
            ),
            Error(
                "Reverse query name for 'Model.m2m' clashes with field name 'Model.clash'.",
                hint=(
                    "Rename field 'Model.clash', or add/change a related_name "
                    "argument to the definition for field 'Model.m2m'."
                ),
                obj=Model._meta.get_field('m2m'),
                id='fields.E303',
            ),
        ])

    def test_valid_model(self):
        class Model(models.Model):
            first = models.ManyToManyField("self", symmetrical=False, related_name='first_accessor')
            second = models.ManyToManyField("self", symmetrical=False, related_name='second_accessor')

        self.assertEqual(Model.check(), [])


@isolate_apps('invalid_models_tests')
class SelfReferentialFKClashTests(SimpleTestCase):

    def test_accessor_clash(self):
        class Model(models.Model):
            model_set = models.ForeignKey("Model", models.CASCADE)

        self.assertEqual(Model.check(), [
            Error(
                "Reverse accessor for 'Model.model_set' clashes with field name 'Model.model_set'.",
                hint=(
                    "Rename field 'Model.model_set', or add/change "
                    "a related_name argument to the definition "
                    "for field 'Model.model_set'."
                ),
                obj=Model._meta.get_field('model_set'),
                id='fields.E302',
            ),
        ])

    def test_reverse_query_name_clash(self):
        class Model(models.Model):
            model = models.ForeignKey("Model", models.CASCADE)

        self.assertEqual(Model.check(), [
            Error(
                "Reverse query name for 'Model.model' clashes with field name 'Model.model'.",
                hint=(
                    "Rename field 'Model.model', or add/change a related_name "
                    "argument to the definition for field 'Model.model'."
                ),
                obj=Model._meta.get_field('model'),
                id='fields.E303',
            ),
        ])

    def test_clash_under_explicit_related_name(self):
        class Model(models.Model):
            clash = models.CharField(max_length=10)
            foreign = models.ForeignKey("Model", models.CASCADE, related_name='clash')

        self.assertEqual(Model.check(), [
            Error(
                "Reverse accessor for 'Model.foreign' clashes with field name 'Model.clash'.",
                hint=(
                    "Rename field 'Model.clash', or add/change a related_name "
                    "argument to the definition for field 'Model.foreign'."
                ),
                obj=Model._meta.get_field('foreign'),
                id='fields.E302',
            ),
            Error(
                "Reverse query name for 'Model.foreign' clashes with field name 'Model.clash'.",
                hint=(
                    "Rename field 'Model.clash', or add/change a related_name "
                    "argument to the definition for field 'Model.foreign'."
                ),
                obj=Model._meta.get_field('foreign'),
                id='fields.E303',
            ),
        ])


@isolate_apps('invalid_models_tests')
class ComplexClashTests(SimpleTestCase):

    # New tests should not be included here, because this is a single,
    # self-contained sanity check, not a test of everything.
    def test_complex_clash(self):
        class Target(models.Model):
            tgt_safe = models.CharField(max_length=10)
            clash = models.CharField(max_length=10)
            model = models.CharField(max_length=10)

            clash1_set = models.CharField(max_length=10)

        class Model(models.Model):
            src_safe = models.CharField(max_length=10)

            foreign_1 = models.ForeignKey(Target, models.CASCADE, related_name='id')
            foreign_2 = models.ForeignKey(Target, models.CASCADE, related_name='src_safe')

            m2m_1 = models.ManyToManyField(Target, related_name='id')
            m2m_2 = models.ManyToManyField(Target, related_name='src_safe')

        self.assertEqual(Model.check(), [
            Error(
                "Reverse accessor for 'Model.foreign_1' clashes with field name 'Target.id'.",
                hint=("Rename field 'Target.id', or add/change a related_name "
                      "argument to the definition for field 'Model.foreign_1'."),
                obj=Model._meta.get_field('foreign_1'),
                id='fields.E302',
            ),
            Error(
                "Reverse query name for 'Model.foreign_1' clashes with field name 'Target.id'.",
                hint=("Rename field 'Target.id', or add/change a related_name "
                      "argument to the definition for field 'Model.foreign_1'."),
                obj=Model._meta.get_field('foreign_1'),
                id='fields.E303',
            ),
            Error(
                "Reverse accessor for 'Model.foreign_1' clashes with reverse accessor for 'Model.m2m_1'.",
                hint=("Add or change a related_name argument to "
                      "the definition for 'Model.foreign_1' or 'Model.m2m_1'."),
                obj=Model._meta.get_field('foreign_1'),
                id='fields.E304',
            ),
            Error(
                "Reverse query name for 'Model.foreign_1' clashes with reverse query name for 'Model.m2m_1'.",
                hint=("Add or change a related_name argument to "
                      "the definition for 'Model.foreign_1' or 'Model.m2m_1'."),
                obj=Model._meta.get_field('foreign_1'),
                id='fields.E305',
            ),

            Error(
                "Reverse accessor for 'Model.foreign_2' clashes with reverse accessor for 'Model.m2m_2'.",
                hint=("Add or change a related_name argument "
                      "to the definition for 'Model.foreign_2' or 'Model.m2m_2'."),
                obj=Model._meta.get_field('foreign_2'),
                id='fields.E304',
            ),
            Error(
                "Reverse query name for 'Model.foreign_2' clashes with reverse query name for 'Model.m2m_2'.",
                hint=("Add or change a related_name argument to "
                      "the definition for 'Model.foreign_2' or 'Model.m2m_2'."),
                obj=Model._meta.get_field('foreign_2'),
                id='fields.E305',
            ),

            Error(
                "Reverse accessor for 'Model.m2m_1' clashes with field name 'Target.id'.",
                hint=("Rename field 'Target.id', or add/change a related_name "
                      "argument to the definition for field 'Model.m2m_1'."),
                obj=Model._meta.get_field('m2m_1'),
                id='fields.E302',
            ),
            Error(
                "Reverse query name for 'Model.m2m_1' clashes with field name 'Target.id'.",
                hint=("Rename field 'Target.id', or add/change a related_name "
                      "argument to the definition for field 'Model.m2m_1'."),
                obj=Model._meta.get_field('m2m_1'),
                id='fields.E303',
            ),
            Error(
                "Reverse accessor for 'Model.m2m_1' clashes with reverse accessor for 'Model.foreign_1'.",
                hint=("Add or change a related_name argument to the definition "
                      "for 'Model.m2m_1' or 'Model.foreign_1'."),
                obj=Model._meta.get_field('m2m_1'),
                id='fields.E304',
            ),
            Error(
                "Reverse query name for 'Model.m2m_1' clashes with reverse query name for 'Model.foreign_1'.",
                hint=("Add or change a related_name argument to "
                      "the definition for 'Model.m2m_1' or 'Model.foreign_1'."),
                obj=Model._meta.get_field('m2m_1'),
                id='fields.E305',
            ),

            Error(
                "Reverse accessor for 'Model.m2m_2' clashes with reverse accessor for 'Model.foreign_2'.",
                hint=("Add or change a related_name argument to the definition "
                      "for 'Model.m2m_2' or 'Model.foreign_2'."),
                obj=Model._meta.get_field('m2m_2'),
                id='fields.E304',
            ),
            Error(
                "Reverse query name for 'Model.m2m_2' clashes with reverse query name for 'Model.foreign_2'.",
                hint=("Add or change a related_name argument to the definition "
                      "for 'Model.m2m_2' or 'Model.foreign_2'."),
                obj=Model._meta.get_field('m2m_2'),
                id='fields.E305',
            ),
        ])


@isolate_apps('invalid_models_tests')
class M2mThroughFieldsTests(SimpleTestCase):
    def test_m2m_field_argument_validation(self):
        """
        ManyToManyField accepts the ``through_fields`` kwarg
        only if an intermediary table is specified.
        """
        class Fan(models.Model):
            pass

        with self.assertRaisesMessage(ValueError, 'Cannot specify through_fields without a through model'):
            models.ManyToManyField(Fan, through_fields=('f1', 'f2'))

    def test_invalid_order(self):
        """
        Mixing up the order of link fields to ManyToManyField.through_fields
        triggers validation errors.
        """
        class Fan(models.Model):
            pass

        class Event(models.Model):
            invitees = models.ManyToManyField(Fan, through='Invitation', through_fields=('invitee', 'event'))

        class Invitation(models.Model):
            event = models.ForeignKey(Event, models.CASCADE)
            invitee = models.ForeignKey(Fan, models.CASCADE)
            inviter = models.ForeignKey(Fan, models.CASCADE, related_name='+')

        field = Event._meta.get_field('invitees')
        self.assertEqual(field.check(from_model=Event), [
            Error(
                "'Invitation.invitee' is not a foreign key to 'Event'.",
                hint="Did you mean one of the following foreign keys to 'Event': event?",
                obj=field,
                id='fields.E339',
            ),
            Error(
                "'Invitation.event' is not a foreign key to 'Fan'.",
                hint="Did you mean one of the following foreign keys to 'Fan': invitee, inviter?",
                obj=field,
                id='fields.E339',
            ),
        ])

    def test_invalid_field(self):
        """
        Providing invalid field names to ManyToManyField.through_fields
        triggers validation errors.
        """
        class Fan(models.Model):
            pass

        class Event(models.Model):
            invitees = models.ManyToManyField(
                Fan,
                through='Invitation',
                through_fields=('invalid_field_1', 'invalid_field_2'),
            )

        class Invitation(models.Model):
            event = models.ForeignKey(Event, models.CASCADE)
            invitee = models.ForeignKey(Fan, models.CASCADE)
            inviter = models.ForeignKey(Fan, models.CASCADE, related_name='+')

        field = Event._meta.get_field('invitees')
        self.assertEqual(field.check(from_model=Event), [
            Error(
                "The intermediary model 'invalid_models_tests.Invitation' has no field 'invalid_field_1'.",
                hint="Did you mean one of the following foreign keys to 'Event': event?",
                obj=field,
                id='fields.E338',
            ),
            Error(
                "The intermediary model 'invalid_models_tests.Invitation' has no field 'invalid_field_2'.",
                hint="Did you mean one of the following foreign keys to 'Fan': invitee, inviter?",
                obj=field,
                id='fields.E338',
            ),
        ])

    def test_explicit_field_names(self):
        """
        If ``through_fields`` kwarg is given, it must specify both
        link fields of the intermediary table.
        """
        class Fan(models.Model):
            pass

        class Event(models.Model):
            invitees = models.ManyToManyField(Fan, through='Invitation', through_fields=(None, 'invitee'))

        class Invitation(models.Model):
            event = models.ForeignKey(Event, models.CASCADE)
            invitee = models.ForeignKey(Fan, models.CASCADE)
            inviter = models.ForeignKey(Fan, models.CASCADE, related_name='+')

        field = Event._meta.get_field('invitees')
        self.assertEqual(field.check(from_model=Event), [
            Error(
                "Field specifies 'through_fields' but does not provide the names "
                "of the two link fields that should be used for the relation "
                "through model 'invalid_models_tests.Invitation'.",
                hint="Make sure you specify 'through_fields' as through_fields=('field1', 'field2')",
                obj=field,
                id='fields.E337',
            ),
        ])

    def test_superset_foreign_object(self):
        class Parent(models.Model):
            a = models.PositiveIntegerField()
            b = models.PositiveIntegerField()
            c = models.PositiveIntegerField()

            class Meta:
                unique_together = (('a', 'b', 'c'),)

        class Child(models.Model):
            a = models.PositiveIntegerField()
            b = models.PositiveIntegerField()
            value = models.CharField(max_length=255)
            parent = ForeignObject(
                Parent,
                on_delete=models.SET_NULL,
                from_fields=('a', 'b'),
                to_fields=('a', 'b'),
                related_name='children',
            )

        field = Child._meta.get_field('parent')
        self.assertEqual(field.check(from_model=Child), [
            Error(
                "No subset of the fields 'a', 'b' on model 'Parent' is unique.",
                hint=(
                    "Add unique=True on any of those fields or add at least "
                    "a subset of them to a unique_together constraint."
                ),
                obj=field,
                id='fields.E310',
            ),
        ])

    def test_intersection_foreign_object(self):
        class Parent(models.Model):
            a = models.PositiveIntegerField()
            b = models.PositiveIntegerField()
            c = models.PositiveIntegerField()
            d = models.PositiveIntegerField()

            class Meta:
                unique_together = (('a', 'b', 'c'),)

        class Child(models.Model):
            a = models.PositiveIntegerField()
            b = models.PositiveIntegerField()
            d = models.PositiveIntegerField()
            value = models.CharField(max_length=255)
            parent = ForeignObject(
                Parent,
                on_delete=models.SET_NULL,
                from_fields=('a', 'b', 'd'),
                to_fields=('a', 'b', 'd'),
                related_name='children',
            )

        field = Child._meta.get_field('parent')
        self.assertEqual(field.check(from_model=Child), [
            Error(
                "No subset of the fields 'a', 'b', 'd' on model 'Parent' is unique.",
                hint=(
                    "Add unique=True on any of those fields or add at least "
                    "a subset of them to a unique_together constraint."
                ),
                obj=field,
                id='fields.E310',
            ),
        ])
from django.core import checks
from django.db import models
from django.test import SimpleTestCase
from django.test.utils import isolate_apps


@isolate_apps('invalid_models_tests')
class DeprecatedFieldsTests(SimpleTestCase):
    def test_IPAddressField_deprecated(self):
        class IPAddressModel(models.Model):
            ip = models.IPAddressField()

        model = IPAddressModel()
        self.assertEqual(
            model.check(),
            [checks.Error(
                'IPAddressField has been removed except for support in '
                'historical migrations.',
                hint='Use GenericIPAddressField instead.',
                obj=IPAddressModel._meta.get_field('ip'),
                id='fields.E900',
            )],
        )

    def test_CommaSeparatedIntegerField_deprecated(self):
        class CommaSeparatedIntegerModel(models.Model):
            csi = models.CommaSeparatedIntegerField(max_length=64)

        model = CommaSeparatedIntegerModel()
        self.assertEqual(
            model.check(),
            [checks.Error(
                'CommaSeparatedIntegerField is removed except for support in '
                'historical migrations.',
                hint='Use CharField(validators=[validate_comma_separated_integer_list]) instead.',
                obj=CommaSeparatedIntegerModel._meta.get_field('csi'),
                id='fields.E901',
            )],
        )
from unittest import mock

from django.core.checks import Error
from django.db import connections, models
from django.test import SimpleTestCase
from django.test.utils import isolate_apps


def dummy_allow_migrate(db, app_label, **hints):
    # Prevent checks from being run on the 'other' database, which doesn't have
    # its check_field() method mocked in the test.
    return db == 'default'


@isolate_apps('invalid_models_tests')
class BackendSpecificChecksTests(SimpleTestCase):

    @mock.patch('django.db.models.fields.router.allow_migrate', new=dummy_allow_migrate)
    def test_check_field(self):
        """ Test if backend specific checks are performed. """
        error = Error('an error')

        class Model(models.Model):
            field = models.IntegerField()

        field = Model._meta.get_field('field')
        with mock.patch.object(connections['default'].validation, 'check_field', return_value=[error]):
            self.assertEqual(field.check(), [error])
from django.db import models
from django.test import SimpleTestCase
from django.test.utils import isolate_apps


@isolate_apps('invalid_models_tests')
class CustomFieldTest(SimpleTestCase):

    def test_none_column(self):
        class NoColumnField(models.AutoField):
            def db_type(self, connection):
                # None indicates not to create a column in the database.
                return None

        class Model(models.Model):
            field = NoColumnField(primary_key=True, db_column="other_field")
            other_field = models.IntegerField()

        field = Model._meta.get_field('field')
        self.assertEqual(field.check(), [])
import unittest

from django.core.checks import Error, Warning as DjangoWarning
from django.db import connection, models
from django.test import SimpleTestCase, TestCase, skipIfDBFeature
from django.test.utils import isolate_apps, override_settings
from django.utils.functional import lazy
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _


@isolate_apps('invalid_models_tests')
class AutoFieldTests(SimpleTestCase):

    def test_valid_case(self):
        class Model(models.Model):
            id = models.AutoField(primary_key=True)

        field = Model._meta.get_field('id')
        self.assertEqual(field.check(), [])

    def test_primary_key(self):
        # primary_key must be True. Refs #12467.
        class Model(models.Model):
            field = models.AutoField(primary_key=False)

            # Prevent Django from autocreating `id` AutoField, which would
            # result in an error, because a model must have exactly one
            # AutoField.
            another = models.IntegerField(primary_key=True)

        field = Model._meta.get_field('field')
        self.assertEqual(field.check(), [
            Error(
                'AutoFields must set primary_key=True.',
                obj=field,
                id='fields.E100',
            ),
        ])


@isolate_apps('invalid_models_tests')
class BinaryFieldTests(SimpleTestCase):

    def test_valid_default_value(self):
        class Model(models.Model):
            field1 = models.BinaryField(default=b'test')
            field2 = models.BinaryField(default=None)

        for field_name in ('field1', 'field2'):
            field = Model._meta.get_field(field_name)
            self.assertEqual(field.check(), [])

    def test_str_default_value(self):
        class Model(models.Model):
            field = models.BinaryField(default='test')

        field = Model._meta.get_field('field')
        self.assertEqual(field.check(), [
            Error(
                "BinaryField's default cannot be a string. Use bytes content "
                "instead.",
                obj=field,
                id='fields.E170',
            ),
        ])


@isolate_apps('invalid_models_tests')
class CharFieldTests(SimpleTestCase):

    def test_valid_field(self):
        class Model(models.Model):
            field = models.CharField(
                max_length=255,
                choices=[
                    ('1', 'item1'),
                    ('2', 'item2'),
                ],
                db_index=True,
            )

        field = Model._meta.get_field('field')
        self.assertEqual(field.check(), [])

    def test_missing_max_length(self):
        class Model(models.Model):
            field = models.CharField()

        field = Model._meta.get_field('field')
        self.assertEqual(field.check(), [
            Error(
                "CharFields must define a 'max_length' attribute.",
                obj=field,
                id='fields.E120',
            ),
        ])

    def test_negative_max_length(self):
        class Model(models.Model):
            field = models.CharField(max_length=-1)

        field = Model._meta.get_field('field')
        self.assertEqual(field.check(), [
            Error(
                "'max_length' must be a positive integer.",
                obj=field,
                id='fields.E121',
            ),
        ])

    def test_bad_max_length_value(self):
        class Model(models.Model):
            field = models.CharField(max_length="bad")

        field = Model._meta.get_field('field')
        self.assertEqual(field.check(), [
            Error(
                "'max_length' must be a positive integer.",
                obj=field,
                id='fields.E121',
            ),
        ])

    def test_str_max_length_value(self):
        class Model(models.Model):
            field = models.CharField(max_length='20')

        field = Model._meta.get_field('field')
        self.assertEqual(field.check(), [
            Error(
                "'max_length' must be a positive integer.",
                obj=field,
                id='fields.E121',
            ),
        ])

    def test_str_max_length_type(self):
        class Model(models.Model):
            field = models.CharField(max_length=True)

        field = Model._meta.get_field('field')
        self.assertEqual(field.check(), [
            Error(
                "'max_length' must be a positive integer.",
                obj=field,
                id='fields.E121'
            ),
        ])

    def test_non_iterable_choices(self):
        class Model(models.Model):
            field = models.CharField(max_length=10, choices='bad')

        field = Model._meta.get_field('field')
        self.assertEqual(field.check(), [
            Error(
                "'choices' must be an iterable (e.g., a list or tuple).",
                obj=field,
                id='fields.E004',
            ),
        ])

    def test_non_iterable_choices_two_letters(self):
        """Two letters isn't a valid choice pair."""
        class Model(models.Model):
            field = models.CharField(max_length=10, choices=['ab'])

        field = Model._meta.get_field('field')
        self.assertEqual(field.check(), [
            Error(
                "'choices' must be an iterable containing (actual value, "
                "human readable name) tuples.",
                obj=field,
                id='fields.E005',
            ),
        ])

    def test_iterable_of_iterable_choices(self):
        class ThingItem:
            def __init__(self, value, display):
                self.value = value
                self.display = display

            def __iter__(self):
                return iter((self.value, self.display))

            def __len__(self):
                return 2

        class Things:
            def __iter__(self):
                return iter((ThingItem(1, 2), ThingItem(3, 4)))

        class ThingWithIterableChoices(models.Model):
            thing = models.CharField(max_length=100, blank=True, choices=Things())

        self.assertEqual(ThingWithIterableChoices._meta.get_field('thing').check(), [])

    def test_choices_containing_non_pairs(self):
        class Model(models.Model):
            field = models.CharField(max_length=10, choices=[(1, 2, 3), (1, 2, 3)])

        class Model2(models.Model):
            field = models.IntegerField(choices=[0])

        for model in (Model, Model2):
            with self.subTest(model.__name__):
                field = model._meta.get_field('field')
                self.assertEqual(field.check(), [
                    Error(
                        "'choices' must be an iterable containing (actual "
                        "value, human readable name) tuples.",
                        obj=field,
                        id='fields.E005',
                    ),
                ])

    def test_choices_containing_lazy(self):
        class Model(models.Model):
            field = models.CharField(max_length=10, choices=[['1', _('1')], ['2', _('2')]])

        self.assertEqual(Model._meta.get_field('field').check(), [])

    def test_lazy_choices(self):
        class Model(models.Model):
            field = models.CharField(max_length=10, choices=lazy(lambda: [[1, '1'], [2, '2']], tuple)())

        self.assertEqual(Model._meta.get_field('field').check(), [])

    def test_choices_named_group(self):
        class Model(models.Model):
            field = models.CharField(
                max_length=10, choices=[
                    ['knights', [['L', 'Lancelot'], ['G', 'Galahad']]],
                    ['wizards', [['T', 'Tim the Enchanter']]],
                    ['R', 'Random character'],
                ],
            )

        self.assertEqual(Model._meta.get_field('field').check(), [])

    def test_choices_named_group_non_pairs(self):
        class Model(models.Model):
            field = models.CharField(
                max_length=10,
                choices=[['knights', [['L', 'Lancelot', 'Du Lac']]]],
            )

        field = Model._meta.get_field('field')
        self.assertEqual(field.check(), [
            Error(
                "'choices' must be an iterable containing (actual value, "
                "human readable name) tuples.",
                obj=field,
                id='fields.E005',
            ),
        ])

    def test_choices_named_group_bad_structure(self):
        class Model(models.Model):
            field = models.CharField(
                max_length=10, choices=[
                    ['knights', [
                        ['Noble', [['G', 'Galahad']]],
                        ['Combative', [['L', 'Lancelot']]],
                    ]],
                ],
            )

        field = Model._meta.get_field('field')
        self.assertEqual(field.check(), [
            Error(
                "'choices' must be an iterable containing (actual value, "
                "human readable name) tuples.",
                obj=field,
                id='fields.E005',
            ),
        ])

    def test_choices_named_group_lazy(self):
        class Model(models.Model):
            field = models.CharField(
                max_length=10, choices=[
                    [_('knights'), [['L', _('Lancelot')], ['G', _('Galahad')]]],
                    ['R', _('Random character')],
                ],
            )

        self.assertEqual(Model._meta.get_field('field').check(), [])

    def test_bad_db_index_value(self):
        class Model(models.Model):
            field = models.CharField(max_length=10, db_index='bad')

        field = Model._meta.get_field('field')
        self.assertEqual(field.check(), [
            Error(
                "'db_index' must be None, True or False.",
                obj=field,
                id='fields.E006',
            ),
        ])

    def test_bad_validators(self):
        class Model(models.Model):
            field = models.CharField(max_length=10, validators=[True])

        field = Model._meta.get_field('field')
        self.assertEqual(field.check(), [
            Error(
                "All 'validators' must be callable.",
                hint=(
                    "validators[0] (True) isn't a function or instance of a "
                    "validator class."
                ),
                obj=field,
                id='fields.E008',
            ),
        ])

    @unittest.skipUnless(connection.vendor == 'mysql',
                         "Test valid only for MySQL")
    def test_too_long_char_field_under_mysql(self):
        from django.db.backends.mysql.validation import DatabaseValidation

        class Model(models.Model):
            field = models.CharField(unique=True, max_length=256)

        field = Model._meta.get_field('field')
        validator = DatabaseValidation(connection=connection)
        self.assertEqual(validator.check_field(field), [
            Error(
                'MySQL does not allow unique CharFields to have a max_length > 255.',
                obj=field,
                id='mysql.E001',
            )
        ])


@isolate_apps('invalid_models_tests')
class DateFieldTests(SimpleTestCase):
    maxDiff = None

    def test_auto_now_and_auto_now_add_raise_error(self):
        class Model(models.Model):
            field0 = models.DateTimeField(auto_now=True, auto_now_add=True, default=now)
            field1 = models.DateTimeField(auto_now=True, auto_now_add=False, default=now)
            field2 = models.DateTimeField(auto_now=False, auto_now_add=True, default=now)
            field3 = models.DateTimeField(auto_now=True, auto_now_add=True, default=None)

        expected = []
        checks = []
        for i in range(4):
            field = Model._meta.get_field('field%d' % i)
            expected.append(Error(
                "The options auto_now, auto_now_add, and default "
                "are mutually exclusive. Only one of these options "
                "may be present.",
                obj=field,
                id='fields.E160',
            ))
            checks.extend(field.check())
            self.assertEqual(checks, expected)

    def test_fix_default_value(self):
        class Model(models.Model):
            field_dt = models.DateField(default=now())
            field_d = models.DateField(default=now().date())
            field_now = models.DateField(default=now)

        field_dt = Model._meta.get_field('field_dt')
        field_d = Model._meta.get_field('field_d')
        field_now = Model._meta.get_field('field_now')
        errors = field_dt.check()
        errors.extend(field_d.check())
        errors.extend(field_now.check())  # doesn't raise a warning
