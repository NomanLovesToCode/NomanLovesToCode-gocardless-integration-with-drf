# subscriptions/management/commands/test_gocardless.py
"""
Management command to test GoCardless integration.

Usage:
    python manage.py test_gocardless --check-connection
    python manage.py test_gocardless --check-mandate <mandate_id>
    python manage.py test_gocardless --check-subscription <subscription_id>
    python manage.py test_gocardless --sync-user <user_email>
    python manage.py test_gocardless --list-pending
    python manage.py test_gocardless --list-all
    python manage.py test_gocardless --cleanup-stale
"""

from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from Helyar1_Backend.clients import gocardless_client
from accounts.models import User
from subscriptions.models import Subscription
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Test GoCardless integration and sync data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--check-connection',
            action='store_true',
            help='Check GoCardless API connection',
        )
        parser.add_argument(
            '--check-mandate',
            type=str,
            help='Check specific mandate status',
        )
        parser.add_argument(
            '--check-subscription',
            type=str,
            help='Check specific subscription status',
        )
        parser.add_argument(
            '--sync-user',
            type=str,
            help='Sync subscription for specific user by email',
        )
        parser.add_argument(
            '--list-pending',
            action='store_true',
            help='List all pending subscriptions',
        )
        parser.add_argument(
            '--list-all',
            action='store_true',
            help='List all subscriptions with their status',
        )
        parser.add_argument(
            '--cleanup-stale',
            action='store_true',
            help='Cleanup stale pending subscriptions (>24 hours)',
        )
        parser.add_argument(
            '--check-billing-request',
            type=str,
            help='Check specific billing request status',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS('GoCardless Integration Test Tool'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
        
        if options['check_connection']:
            self.check_connection()
        
        elif options['check_mandate']:
            self.check_mandate(options['check_mandate'])
        
        elif options['check_subscription']:
            self.check_subscription(options['check_subscription'])
        
        elif options['sync_user']:
            self.sync_user(options['sync_user'])
        
        elif options['list_pending']:
            self.list_pending()
        
        elif options['list_all']:
            self.list_all()
        
        elif options['cleanup_stale']:
            self.cleanup_stale()
        
        elif options['check_billing_request']:
            self.check_billing_request(options['check_billing_request'])
        
        else:
            self.stdout.write(self.style.WARNING('\nNo action specified. Available options:'))
            self.stdout.write('  --check-connection')
            self.stdout.write('  --check-mandate <mandate_id>')
            self.stdout.write('  --check-subscription <subscription_id>')
            self.stdout.write('  --check-billing-request <billing_request_id>')
            self.stdout.write('  --sync-user <user_email>')
            self.stdout.write('  --list-pending')
            self.stdout.write('  --list-all')
            self.stdout.write('  --cleanup-stale')
            self.stdout.write('\nUse --help for more information.')

    def check_connection(self):
        """Test GoCardless API connection"""
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write('Checking GoCardless Connection')
        self.stdout.write('=' * 60)
        
        try:
            # Try to list creditors (your account info)
            creditors = gocardless_client.creditors.list()
            
            self.stdout.write(self.style.SUCCESS('\n✓ Connected to GoCardless successfully!'))
            self.stdout.write(f'\nEnvironment: {self.style.WARNING(settings.GC_ENVIRONMENT)}')
            
            if creditors.records:
                creditor = creditors.records[0]
                self.stdout.write(f'Account Name: {creditor.name}')
                self.stdout.write(f'Creditor ID: {creditor.id}')
                if hasattr(creditor, 'scheme_identifiers'):
                    self.stdout.write(f'Schemes: {", ".join([s.scheme for s in creditor.scheme_identifiers])}')
            
            # Test webhook endpoint
            self.stdout.write(f'\nWebhook Endpoint: {settings.BASE_BACKEND_URL}/api/subscriptions/webhook/')
            self.stdout.write(f'Redirect URI: {settings.BASE_BACKEND_URL}/api/subscriptions/gocardless-complete/')
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'\n✗ Connection failed: {str(e)}'))
            self.stdout.write(self.style.WARNING('\nTroubleshooting:'))
            self.stdout.write('1. Check GC_ACCESS_TOKEN in .env')
            self.stdout.write('2. Verify GC_ENVIRONMENT is correct (sandbox/live)')
            self.stdout.write('3. Check internet connection')

    def check_mandate(self, mandate_id):
        """Check mandate status"""
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(f'Checking Mandate: {mandate_id}')
        self.stdout.write('=' * 60)
        
        try:
            mandate = gocardless_client.mandates.get(mandate_id)
            
            self.stdout.write(self.style.SUCCESS('\n✓ Mandate found!'))
            self.stdout.write(f'\nStatus: {self._colorize_status(mandate.status)}')
            self.stdout.write(f'Scheme: {mandate.scheme}')
            self.stdout.write(f'Reference: {mandate.reference}')
            self.stdout.write(f'Created: {mandate.created_at}')
            
            if hasattr(mandate, 'links'):
                self.stdout.write(f'\nCustomer ID: {mandate.links.customer}')
                
                # Try to get customer details
                try:
                    customer = gocardless_client.customers.get(mandate.links.customer)
                    self.stdout.write(f'Customer Name: {customer.given_name} {customer.family_name}')
                    self.stdout.write(f'Customer Email: {customer.email}')
                except:
                    pass
            
            # Check for associated subscriptions
            if hasattr(mandate, 'links') and hasattr(mandate.links, 'customer'):
                try:
                    subs = gocardless_client.subscriptions.list(params={'mandate': mandate_id})
                    if subs.records:
                        self.stdout.write(f'\n{len(subs.records)} subscription(s) found:')
                        for sub in subs.records:
                            self.stdout.write(f'  - {sub.id} ({sub.status})')
                except:
                    pass
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'\n✗ Failed: {str(e)}'))

    def check_subscription(self, subscription_id):
        """Check subscription status"""
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(f'Checking Subscription: {subscription_id}')
        self.stdout.write('=' * 60)
        
        try:
            subscription = gocardless_client.subscriptions.get(subscription_id)
            
            self.stdout.write(self.style.SUCCESS('\n✓ Subscription found!'))
            self.stdout.write(f'\nStatus: {self._colorize_status(subscription.status)}')
            self.stdout.write(f'Amount: {subscription.amount / 100} {subscription.currency}')
            self.stdout.write(f'Interval: Every {subscription.interval} {subscription.interval_unit}(s)')
            self.stdout.write(f'Created: {subscription.created_at}')
            
            if hasattr(subscription, 'start_date'):
                self.stdout.write(f'Start Date: {subscription.start_date}')
            
            if hasattr(subscription, 'end_date') and subscription.end_date:
                self.stdout.write(f'End Date: {subscription.end_date}')
            
            if hasattr(subscription, 'upcoming_payments') and subscription.upcoming_payments:
                self.stdout.write('\nUpcoming Payments:')
                for payment in subscription.upcoming_payments[:3]:  # Show first 3
                    amount = payment.get('amount', 0) / 100
                    charge_date = payment.get('charge_date', 'N/A')
                    self.stdout.write(f'  - {charge_date}: {amount} {subscription.currency}')
            
            # Check local database
            try:
                local_sub = Subscription.objects.get(subscription_id=subscription_id)
                self.stdout.write('\n' + '-' * 60)
                self.stdout.write('Local Database:')
                self.stdout.write(f'User: {local_sub.user.email}')
                self.stdout.write(f'Local Status: {local_sub.status}')
                self.stdout.write(f'Active: {local_sub.is_active}')
                self.stdout.write(f'Expires: {local_sub.expires_at}')
                
                if subscription.status != local_sub.status:
                    self.stdout.write(self.style.WARNING(
                        f'\n⚠ Status mismatch! GC: {subscription.status}, Local: {local_sub.status}'
                    ))
            except Subscription.DoesNotExist:
                self.stdout.write(self.style.WARNING('\n⚠ Not found in local database'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'\n✗ Failed: {str(e)}'))

    def check_billing_request(self, billing_request_id):
        """Check billing request status"""
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(f'Checking Billing Request: {billing_request_id}')
        self.stdout.write('=' * 60)
        
        try:
            billing_request = gocardless_client.billing_requests.get(billing_request_id)
            
            self.stdout.write(self.style.SUCCESS('\n✓ Billing Request found!'))
            self.stdout.write(f'\nStatus: {self._colorize_status(billing_request.status)}')
            self.stdout.write(f'Created: {billing_request.created_at}')
            
            if hasattr(billing_request, 'links'):
                links = billing_request.links
                if hasattr(links, 'customer') and links.customer:
                    self.stdout.write(f'Customer ID: {links.customer}')
                if hasattr(links, 'mandate_request_mandate') and links.mandate_request_mandate:
                    self.stdout.write(f'Mandate ID: {links.mandate_request_mandate}')
                if hasattr(links, 'payment') and links.payment:
                    self.stdout.write(f'Payment ID: {links.payment}')
            
            # Check local database
            try:
                local_sub = Subscription.objects.get(temp_billing_request_id=billing_request_id)
                self.stdout.write('\n' + '-' * 60)
                self.stdout.write('Local Database:')
                self.stdout.write(f'User: {local_sub.user.email}')
                self.stdout.write(f'Status: {local_sub.status}')
                self.stdout.write(f'Flow ID: {local_sub.temp_flow_id}')
            except Subscription.DoesNotExist:
                self.stdout.write(self.style.WARNING('\n⚠ Not found in local database'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'\n✗ Failed: {str(e)}'))

    def sync_user(self, email):
        """Sync subscription data for a specific user"""
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(f'Syncing User: {email}')
        self.stdout.write('=' * 60)
        
        try:
            user = User.objects.get(email=email)
            self.stdout.write(f'\n✓ Found user: {user.email} (ID: {user.id})')
            
            # Check if user has subscription
            try:
                subscription = Subscription.objects.get(user=user)
                self.stdout.write('\n' + '-' * 60)
                self.stdout.write('Local Subscription:')
                self.stdout.write(f'  Status: {subscription.status}')
                self.stdout.write(f'  Active: {subscription.is_active}')
                self.stdout.write(f'  Valid: {subscription.is_valid()}')
                self.stdout.write(f'  Created: {subscription.created_at}')
                self.stdout.write(f'  Expires: {subscription.expires_at}')
                self.stdout.write(f'  GC Sub ID: {subscription.subscription_id or "N/A"}')
                
                # Check mandate
                if hasattr(user, 'profile') and user.profile.mandate_id:
                    self.stdout.write(f'  Mandate ID: {user.profile.mandate_id}')
                    self.stdout.write(f'  Customer ID: {user.profile.customer_id}')
                    
                    # Fetch from GoCardless
                    try:
                        mandate = gocardless_client.mandates.get(user.profile.mandate_id)
                        status_colored = self._colorize_status(mandate.status)
                        self.stdout.write(f'\n  GoCardless Mandate: {status_colored}')
                        
                        if mandate.status != 'active':
                            self.stdout.write(self.style.WARNING(
                                f'  ⚠ Mandate is not active!'
                            ))
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f'  Could not fetch mandate: {str(e)}'))
                else:
                    self.stdout.write(self.style.WARNING('  ⚠ No mandate set'))
                
                # Check subscription on GoCardless
                if subscription.subscription_id:
                    try:
                        gc_sub = gocardless_client.subscriptions.get(subscription.subscription_id)
                        status_colored = self._colorize_status(gc_sub.status)
                        self.stdout.write(f'\n  GoCardless Subscription: {status_colored}')
                        
                        # Compare and suggest sync
                        if gc_sub.status != subscription.status:
                            self.stdout.write(self.style.WARNING(
                                f'\n  ⚠ Status mismatch! Local: {subscription.status}, GC: {gc_sub.status}'
                            ))
                            
                            response = input('\n  Sync with GoCardless? (y/n): ')
                            if response.lower() == 'y':
                                self._sync_subscription(subscription, gc_sub)
                        else:
                            self.stdout.write(self.style.SUCCESS('  ✓ Status in sync'))
                        
                        # Show upcoming payments
                        if hasattr(gc_sub, 'upcoming_payments') and gc_sub.upcoming_payments:
                            self.stdout.write('\n  Next Payment:')
                            next_payment = gc_sub.upcoming_payments[0]
                            self.stdout.write(f'    Date: {next_payment["charge_date"]}')
                            self.stdout.write(f'    Amount: {next_payment["amount"] / 100} {gc_sub.currency}')
                    
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f'\n  Could not fetch GC subscription: {str(e)}'))
                else:
                    self.stdout.write(self.style.WARNING('\n  ⚠ No subscription ID set'))
                
            except Subscription.DoesNotExist:
                self.stdout.write(self.style.WARNING('\n⚠ No subscription found for this user'))
                self.stdout.write('\nTo create a subscription, user should:')
                self.stdout.write('1. Call POST /api/subscriptions/create-mandate/')
                self.stdout.write('2. Complete GoCardless flow')
                
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'\n✗ User not found: {email}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'\n✗ Error: {str(e)}'))
            logger.exception(e)

    def _sync_subscription(self, subscription, gc_sub):
        """Sync local subscription with GoCardless data"""
        from datetime import datetime
        
        self.stdout.write('\n  Syncing...')
        
        # Update status
        old_status = subscription.status
        if gc_sub.status == 'active':
            subscription.is_active = True
            subscription.status = 'active'
        elif gc_sub.status == 'cancelled':
            subscription.is_active = False
            subscription.status = 'cancelled'
        elif gc_sub.status == 'finished':
            subscription.is_active = False
            subscription.status = 'expired'
        elif gc_sub.status == 'paused':
            subscription.is_active = False
            subscription.status = 'inactive'
        
        # Update expiry
        if hasattr(gc_sub, 'upcoming_payments') and gc_sub.upcoming_payments:
            try:
                subscription.expires_at = datetime.fromisoformat(
                    gc_sub.upcoming_payments[0]['charge_date'].replace('Z', '+00:00')
                )
            except:
                pass
        
        subscription.save()
        
        # Sync user flags
        subscription.user.subscription_status = subscription.is_active
        subscription.user.save()
        if hasattr(subscription.user, 'profile'):
            subscription.user.profile.subscription_status = subscription.is_active
            subscription.user.profile.save()
        
        self.stdout.write(self.style.SUCCESS(f'  ✓ Synced! {old_status} → {subscription.status}'))

    def list_pending(self):
        """List all pending subscriptions"""
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write('Pending Subscriptions')
        self.stdout.write('=' * 60)
        
        pending = Subscription.objects.filter(status='pending').order_by('-created_at')
        
        if not pending.exists():
            self.stdout.write(self.style.SUCCESS('\n✓ No pending subscriptions'))
            return
        
        self.stdout.write(f'\nFound {pending.count()} pending subscription(s):\n')
        
        for sub in pending:
            self.stdout.write('-' * 60)
            self.stdout.write(f'ID: {sub.id}')
            self.stdout.write(f'User: {sub.user.email}')
            self.stdout.write(f'Created: {sub.created_at}')
            self.stdout.write(f'Billing Request: {sub.temp_billing_request_id or "N/A"}')
            self.stdout.write(f'Flow ID: {sub.temp_flow_id or "N/A"}')
            
            # Check if stale (>24 hours)
            age = timezone.now() - sub.created_at
            hours_old = age.total_seconds() / 3600
            
            if hours_old > 24:
                self.stdout.write(self.style.WARNING(f'⚠ STALE ({int(hours_old)} hours old)'))
            else:
                self.stdout.write(f'Age: {int(hours_old)} hours')
            
            self.stdout.write('')

    def list_all(self):
        """List all subscriptions"""
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write('All Subscriptions')
        self.stdout.write('=' * 60)
        
        subscriptions = Subscription.objects.all().order_by('-created_at')
        
        if not subscriptions.exists():
            self.stdout.write(self.style.WARNING('\n⚠ No subscriptions found'))
            return
        
        # Summary
        total = subscriptions.count()
        active = subscriptions.filter(status='active', is_active=True).count()
        pending = subscriptions.filter(status='pending').count()
        cancelled = subscriptions.filter(status='cancelled').count()
        expired = subscriptions.filter(status='expired').count()
        
        self.stdout.write(f'\nTotal: {total} | Active: {active} | Pending: {pending} | Cancelled: {cancelled} | Expired: {expired}\n')
        
        for sub in subscriptions:
            status_str = self._colorize_status(sub.status)
            active_str = '✓' if sub.is_active else '✗'
            self.stdout.write(f'{sub.id:3d} | {sub.user.email:30s} | {status_str:15s} | Active: {active_str} | Created: {sub.created_at}')

    def cleanup_stale(self):
        """Cleanup stale pending subscriptions"""
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write('Cleaning Up Stale Subscriptions')
        self.stdout.write('=' * 60)
        
        cutoff_time = timezone.now() - timedelta(hours=24)
        stale_subs = Subscription.objects.filter(
            status='pending',
            created_at__lt=cutoff_time
        )
        
        count = stale_subs.count()
        
        if count == 0:
            self.stdout.write(self.style.SUCCESS('\n✓ No stale subscriptions found'))
            return
        
        self.stdout.write(f'\nFound {count} stale subscription(s)')
        
        for sub in stale_subs:
            self.stdout.write(f'\nCleaning: {sub.user.email}')
            self.stdout.write(f'  Created: {sub.created_at}')
            self.stdout.write(f'  Age: {(timezone.now() - sub.created_at).days} days')
        
        response = input(f'\nCleanup {count} stale subscription(s)? (y/n): ')
        
        if response.lower() == 'y':
            for sub in stale_subs:
                sub.clear_temp_fields()
                sub.status = 'inactive'
                sub.save()
            
            self.stdout.write(self.style.SUCCESS(f'\n✓ Cleaned up {count} stale subscription(s)'))
        else:
            self.stdout.write(self.style.WARNING('\nCancelled'))

    def _colorize_status(self, status):
        """Add color to status strings"""
        status_lower = status.lower()
        if status_lower in ['active', 'confirmed', 'paid', 'fulfilled']:
            return self.style.SUCCESS(status)
        elif status_lower in ['pending', 'processing', 'submitted']:
            return self.style.WARNING(status)
        elif status_lower in ['cancelled', 'failed', 'expired', 'inactive']:
            return self.style.ERROR(status)
        else:
            return status