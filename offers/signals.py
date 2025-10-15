# signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Offer
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
    if created and instance.auto_voucher_generation:
        try:
            voucher_count = instance.generate_vouchers()
            logger.info("Vouchers are being created from the signals")            
        except Exception as e:
            logger.error("Error in Voucher generation from the signals because of {e}", exc_info=True)
            raise ValueError(f"✗ Error generating vouchers for {instance.brand_name}: {e}")
            