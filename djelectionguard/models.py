import pickle
import uuid

from django.apps import apps
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import EmailValidator
from django.db import models, transaction
from django.db.models import signals
from django.urls import reverse
from django.utils import timezone

from pymemcache.client.base import Client
from picklefield.fields import PickledObjectField


def emails_validator(value):
    validator = EmailValidator()
    invalid = []
    for line in value.split('\n'):
        line = line.strip()
        if not line:
            continue
        try:
            validator(line)
        except ValidationError:
            invalid.append(line)
    if invalid:
        raise ValidationError(
            'Please remove lines containing invalid emails: '
            + ', '.join(invalid)
        )


class Contest(models.Model):
    id = models.UUIDField(
        primary_key=True,
        editable=False,
        default=uuid.uuid4
    )
    mediator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
    )
    voters_emails = models.TextField(
        validators=[emails_validator],
        help_text='The list of allowed voters with one email per line',
    )
    name = models.CharField(max_length=255)
    type = models.CharField(default='school', max_length=100)
    number_elected = models.IntegerField(default=1)
    votes_allowed = models.IntegerField(default=1)
    number_guardians = models.IntegerField(
        default=1,
        verbose_name='number of guardians',
    )
    quorum = models.IntegerField(
        default=1,
        verbose_name='quorum',
    )
    start = models.DateTimeField()
    end = models.DateTimeField()
    actual_start = models.DateTimeField(null=True, blank=True)
    actual_end = models.DateTimeField(null=True, blank=True)

    joint_public_key = PickledObjectField(null=True, blank=True)
    metadata = PickledObjectField(null=True)
    context = PickledObjectField(null=True)
    device = PickledObjectField(null=True)
    store = PickledObjectField(null=True)
    plaintext_tally = PickledObjectField(null=True)
    ciphertext_tally = PickledObjectField(null=True)
    coefficient_validation_sets = PickledObjectField(null=True)

    @property
    def voters_emails_list(self):
        emails = []
        for line in self.voters_emails.split('\n'):
            line = line.strip()
            if line:
                emails.append(line.lower())
        return emails

    def voters_update(self):
        # delete voters who are not anymore in the email list
        self.voter_set.filter(
            casted=None
        ).exclude(
            user__email__in=self.voters_emails_list
        ).delete()

        # add voters who have a user
        User = apps.get_model(settings.AUTH_USER_MODEL)
        users = User.objects.filter(
            email__in=self.voters_emails_list,
        ).exclude(
            voter__contest=self,
        )
        for user in users:
            self.voter_set.create(user=user)

    @property
    def state(self):
        if self.actual_end:
            return 'finished'
        elif self.actual_start:
            return 'started'
        return 'pending'

    @property
    def variation(self):
        return 'one_of_m' if self.votes_allowed == 1 else 'n_of_m'

    def get_absolute_url(self):
        return reverse('contest_detail', args=[self.pk])

    def get_ballot(self, *selections):
        from electionguard.ballot import (
            PlaintextBallot,
            PlaintextBallotContest,
            PlaintextBallotSelection,
        )
        ballot = PlaintextBallot(
            object_id=uuid.uuid4(),
            ballot_style=f"{self.pk}-style",
            contests=[
                PlaintextBallotContest(
                    object_id=str(self.pk),
                    ballot_selections=[
                        PlaintextBallotSelection(
                            object_id=f"{selection}-selection",
                            vote='True',
                            is_placeholder_selection=False,
                            extended_data=None,
                        ) for selection in selections
                    ]
                )
            ]
        )
        return ballot

    @property
    def description(self):
        from electionguard.election import ElectionDescription
        return ElectionDescription.from_json_object(
            self.get_manifest()
        )

    def prepare(self):
        from electionguard.election_builder import ElectionBuilder
        builder = ElectionBuilder(
            number_of_guardians=self.number_guardians,
            quorum=self.quorum,
            description=self.description,
        )
        builder.set_public_key(self.joint_public_key)
        self.metadata, self.context = builder.build()

        from electionguard.ballot_store import BallotStore
        self.store = BallotStore()

        from electionguard.encrypt import EncryptionDevice, EncryptionMediator
        self.device = EncryptionDevice(str(self.pk))

    @property
    def encrypter(self):
        from electionguard.encrypt import EncryptionMediator
        return EncryptionMediator(
            self.metadata,
            self.context,
            self.device,
        )

    @property
    def ballot_box(self):
        from electionguard.ballot_box import BallotBox
        return BallotBox(self.metadata, self.context, self.store)

    def get_manifest(self):
        return {
            "geopolitical_units": [
                {
                    "type": self.type,
                    "name": self.name,
                    "object_id": str(self.pk) + '-unit',
                },
            ],
            "parties": [],
            "candidates": [
                {
                    "object_id": str(candidate.pk),
                    "ballot_name": {
                        "text": [
                            {
                                "language": 'en',
                                "value": candidate.name,
                            }
                        ]
                    },
                } for candidate in self.candidate_set.all()
            ],
            "contests": [
                {
                    "@type": "CandidateContest",
                    "object_id": str(self.pk),
                    "sequence_order": 0,
                    "ballot_selections": [
                        {
                            "object_id": f"{candidate.pk}-selection",
                            "sequence_order": i,
                            "candidate_id": str(candidate.pk),
                        }
                        for i, candidate in enumerate(self.candidate_set.all())
                    ],
                    "ballot_title": {
                        "text": [
                            {
                                "value": self.name,
                                "language": "en"
                            }
                        ]
                    },
                    "ballot_subtitle": {
                        "text": [
                            {
                                "value": self.name,
                                "language": "en"
                            }
                        ]
                    },
                    "vote_variation": self.variation,
                    "electoral_district_id": f"{self.pk}-unit",
                    "name": self.name,
                    "number_elected": self.number_elected,
                    "votes_allowed": self.votes_allowed,
                }
            ],
            "ballot_styles": [
                {
                    "object_id": f"{self.pk}-style",
                    "geopolitical_unit_ids": [f"{self.pk}-unit"],
                }
            ],
            "name": {
                "text": [
                    {
                        "value": "Test Contest",
                        "language": "en"
                    }
                ]
            },
            "start_date": "2020-03-01T08:00:00-05:00",
            "end_date": "2020-03-01T20:00:00-05:00",
            "election_scope_id": f"{self.pk}-style",
            "type": "primary"
        }

    def __str__(self):
        return self.name


class Candidate(models.Model):
    id = models.UUIDField(
        primary_key=True,
        editable=False,
        default=uuid.uuid4
    )
    contest = models.ForeignKey(
        Contest,
        on_delete=models.CASCADE,
    )
    name = models.CharField(max_length=255)
    score = models.IntegerField(null=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['-score', 'name']


class Guardian(models.Model):
    id = models.UUIDField(
        primary_key=True,
        editable=False,
        default=uuid.uuid4
    )
    contest = models.ForeignKey(
        Contest,
        on_delete=models.CASCADE,
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
    )
    created = models.DateTimeField(auto_now_add=True)
    downloaded = models.DateTimeField(null=True)
    verified = models.DateTimeField(null=True)
    erased = models.DateTimeField(null=True)
    uploaded = models.DateTimeField(null=True)
    uploaded_erased = models.DateTimeField(null=True)

    def __str__(self):
        return str(self.user)

    class Meta:
        ordering = ['created']

    def delete_keypair(self):
        Client(settings.MEMCACHED_HOST).delete(str(self.pk))
        if not self.uploaded:
            self.erased = timezone.now()
        else:
            self.uploaded_erased = timezone.now()
        self.save()

    def upload_keypair(self, content):
        Client(settings.MEMCACHED_HOST).set(str(self.pk), content)
        self.uploaded = timezone.now()
        self.save()

    def get_keypair(self):
        client = Client(settings.MEMCACHED_HOST)
        result = client.get(str(self.pk))
        if not result:
            from electionguard.guardian import Guardian
            guardian = Guardian(
                'guardian',
                0,
                self.contest.number_guardians,
                self.contest.quorum,
            )
            result = pickle.dumps(guardian)
            client.set(str(self.pk), result)
        return result

    def get_guardian(self):
        return pickle.loads(self.get_keypair())


class Voter(models.Model):
    id = models.UUIDField(
        primary_key=True,
        editable=False,
        default=uuid.uuid4
    )
    contest = models.ForeignKey(
        Contest,
        on_delete=models.CASCADE,
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
    )
    casted = models.DateTimeField(null=True)
