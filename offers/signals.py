# signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Offer, Voucher
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Offer)
def generate_vouchers_on_offer_creation(sender, instance, created, **kwargs):
    """
    Automatically generate vouchers when a new offer is created
    if auto_voucher_generation is enabled.
    
    Args:
        sender: The model class (Offer)
        instance: The actual Offer instance being saved
        created: Boolean - True if this is a new record, False if updating
        **kwargs: Additional keyword arguments
    """
    # Only generate vouchers for NEW offers (not updates)
    # and only if auto_voucher_generation is True
    if instance.auto_voucher_generation:
        try:
            existing_count = Voucher.objects.filter(offer=instance).count()
            remaining_to_generate = instance.batch_size - existing_count
            if remaining_to_generate > 0:
                # Temporarily adjust batch_size to generate only the remaining
                original_batch_size = instance.batch_size
                instance.batch_size = remaining_to_generate
                voucher_count = instance.generate_vouchers()
                instance.batch_size = original_batch_size  # Restore original
                logger.info(f"Generated {voucher_count} additional vouchers for Offer {instance.id}")
            else:
                logger.info(f"All {instance.batch_size} vouchers already exist for Offer {instance.id}")
        except Exception as e:
            logger.error(f"Error generating vouchers for {instance.brand_name}: {e}", exc_info=True)
            raise ValueError(f"✗ Error generating vouchers for {instance.brand_name}: {e}")
    
    # If updating an existing offer and auto_voucher_generation is now False,
    # delete all associated vouchers
    if not created and not instance.auto_voucher_generation:
        try:
            vouchers = Voucher.objects.filter(offer=instance)
            if vouchers.exists():
                deleted_count, _ = vouchers.delete()
                logger.info(f"Deleted {deleted_count} vouchers for Offer {instance.id}")
            else:
                logger.info(f"No vouchers found to delete for Offer {instance.id}")
        except Exception as e:
            logger.error(f"Error deleting vouchers for {instance.brand_name}: {e}", exc_info=True)
            # Don't raise here to avoid blocking offer update; log instead