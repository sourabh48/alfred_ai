"""Retain the old command as an explicit, non-mutating decommission notice."""
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help='AWS provisioning is decommissioned. Non-AWS activation requires separate approval.'

    def add_arguments(self,parser):
        parser.add_argument('--user',type=int,required=True)
        parser.add_argument('--bucket',required=True)
        parser.add_argument('--region',required=True)
        parser.add_argument('--account',required=True)

    def handle(self,**options):
        raise CommandError('AWS storage is decommissioned; no credentials were requested or changed.')
