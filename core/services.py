import json
from typing import Optional, Dict, Tuple, TypedDict

import shortuuid as shortuuid

from bctip.local_settings import WALLET
from lnbits import bolt11
from lnbits.bolt11 import Invoice
from wallets.base import PaymentStatus, PaymentResponse
from .models import Payment, Wallet


def create_invoice(wallet_id: int,
                   amount: int,
                   memo: str,
                   description_hash: Optional[bytes] = None,
                   extra: Optional[Dict] = None,
                   webhook: Optional[str] = None) -> Tuple[str, str]:
    invoice_memo = None if description_hash else memo
    storeable_memo = memo

    ok, checking_id, payment_request, error_message = WALLET.create_invoice(
        amount=amount, memo=invoice_memo, description_hash=description_hash
    )
    if not ok:
        raise Exception(error_message or "Unexpected backend error.")

    invoice = bolt11.decode(payment_request)

    amount_msat = amount * 1000
    print(amount_msat)
    Payment.objects.create(wallet_id=wallet_id,
                           checking_id=checking_id,
                           payment_request=payment_request,
                           payment_hash=invoice.payment_hash,
                           amount=amount_msat,
                           memo=storeable_memo,
                           extra=json.dumps(extra) if extra and extra != {} and type(extra) is dict else None,
                           webhook=webhook)

    return invoice.payment_hash, payment_request


def pay_invoice(wallet_id: int,
                payment_request: str,
                max_sat: Optional[int] = None,
                extra: Optional[Dict] = None,
                description: str = "") -> str:
    temp_id: str = f"temp_{shortuuid.uuid()}"
    internal_id: str = f"internal_{shortuuid.uuid()}"
    invoice: Invoice = bolt11.decode(payment_request)
    if invoice.amount_msat == 0:
        raise ValueError("Amountless invoices not supported.")
    if max_sat and invoice.amount_msat > max_sat * 1000:
        raise ValueError("Amount in invoice is too high.")

    # put all parameters that don't change here
    PaymentKwargs = TypedDict(
        "PaymentKwargs", {
            "wallet_id": str,
            "payment_request": str,
            "payment_hash": str,
            "amount": int,
            "memo": str,
            "extra": Optional[Dict],
        },
    )
    payment_kwargs: PaymentKwargs = dict(
        wallet_id=wallet_id,
        payment_request=payment_request,
        payment_hash=invoice.payment_hash,
        amount=-invoice.amount_msat,
        memo=description or invoice.description or "",
        extra=extra
    )
    try:
        payment = Payment.objects.get(payment_hash=invoice.payment_hash,
                                      pending=True,
                                      amount__gt=0)
    except Payment.DoesNotExist:
        payment = None
    if payment:
        Payment.objects.create(checking_id=internal_id, fee=0, pending=False, **payment_kwargs)
    else:
        fee_reserve = max(1000, int(invoice.amount_msat * 0.01))
        Payment.objects.create(checking_id=temp_id, fee=-fee_reserve, **payment_kwargs)
    try:
        wallet = Wallet.objects.get(id=wallet_id)
    except Wallet.DoesNotExist:
        raise ValueError("Wallet {} not found".format(wallet_id))
    if wallet.balance < 0:
        raise PermissionError("Insufficient balance")

    if payment:
        Payment.objects.get(checking_id=payment.checking_id, pending=False)
    else:
        ln_payment: PaymentResponse = WALLET.pay_invoice(payment_request)
        if ln_payment.ok and ln_payment.checking_id:
            Payment.objects.create(checking_id=ln_payment.checking_id, fee=ln_payment.fee_msat,
                                   preimage=ln_payment.preimage, pending=False, **payment_kwargs)
            Payment.objects.filter(checking_id=temp_id).delete()
        else:
            Payment.objects.filter(checking_id=temp_id).delete()
            raise Exception(payment.error_message or "Failed to pay_invoice on backend")

    return invoice.payment_hash


def check_invoice_status(wallet_id: int, payment_hash: str) -> PaymentStatus:
    try:
        payment = Payment.objects.get(wallet_id=wallet_id, payment_hash=payment_hash)
    except Payment.DoesNotExist:
        return PaymentStatus(None)
    return WALLET.get_invoice_status(payment.checking_id)


def get_wallet_balance(wallet_id: int) -> int:
    payments = Payment.objects.filter(wallet_id=wallet_id)
    balance = 0
    for payment in payments:
        if payment.pending:
            status: PaymentStatus = WALLET.get_invoice_status(payment.checking_id)
            if status.paid:
                payment.pending = False
                payment.save()
                balance += payment.amount // 1e8
        else:
            balance += payment.amount // 1e8
    return balance
