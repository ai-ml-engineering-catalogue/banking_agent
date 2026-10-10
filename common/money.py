from decimal import Decimal, ROUND_HALF_UP
def to_paise(rupees):
    return int((Decimal(str(rupees)) * 100).quantize(Decimal('1'), rounding=ROUND_HALF_UP))
def to_rupees(paise): return paise / 100
def format_inr(paise):
    sign = '-' if paise < 0 else ''
    whole, cents = divmod(abs(paise), 100)
    digits = str(whole)
    head, tail = digits[:-3], digits[-3:]
    groups = []
    while head:
        groups.insert(0, head[-2:]); head = head[:-2]
    return f'{sign}₹' + ','.join(groups + [tail]) + f'.{cents:02d}'
