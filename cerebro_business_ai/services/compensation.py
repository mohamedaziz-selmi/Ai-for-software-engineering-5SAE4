"""Multilingual compensation extraction. Values are never currency-converted.

All evidence offsets refer to the original string. A bare 'dinar' is ambiguous;
it is not silently classified as Tunisian currency.
"""
import re
import unicodedata

NUMBER=r"(?:\d{1,3}(?:[ ,.\u00a0\u202f'\u066c]\d{3})+(?:[.,\u066b]\d{1,3})?|\d+(?:[.,\u066b]\d{1,3})?)(?:\s*[kK])?"
CURRENCY=r"(?:dinars?\s+tunisiens?|Tunisian\s+dinars?|dinars?\s+alg[ée]riens?|Algerian\s+dinars?|دينار\s+تونسي|TND|DZD|USD|EUR|GBP|CAD|MAD|DT|euros?|dollars?|livres?\s+sterling|dirhams?|dinars?|دينار|[$€£])"
RANGE=r'(?:to|à|[-–—])'
PERIOD=r'(?:hours?|days?|weeks?|months?|years?|heures?|jours?|semaines?|mois|ans?|ann[ée]es?|شهر|يوم|ساعة)'
PERIOD_SUFFIX=r'(?:(?:\s*(?:/|per\b|par\b|a\b|l[’\x27])\s*'+PERIOD+r')|(?:\s+(?:hourly|daily|weekly|monthly|yearly|annually|mensuels?|mensuelles?|annuels?|annuelles?|شهريا|شهرياً)))?'
AMOUNT=NUMBER+r'(?:\s*'+RANGE+r'\s*(?:'+CURRENCY+r'\s*)?'+NUMBER+r')?'
PAY_PATTERN=r'(?<![\w.,])(?:'+NUMBER+r'\s*'+CURRENCY+r'\s*'+RANGE+r'\s*'+NUMBER+r'\s*'+CURRENCY+r'|'+CURRENCY+r'\s*'+AMOUNT+r'|'+AMOUNT+r'\s*'+CURRENCY+r')(?![\w])'+PERIOD_SUFFIX
HOUR_NUMBER=r'(?:\d+(?:[.,]\d+)?|one|two|three|four|un|une|deux|trois|quatre)'
HOURS_PATTERN=r'\b('+HOUR_NUMBER+r')(?:\s*(?:to|à|[-–—])\s*('+HOUR_NUMBER+r'))?\s*(?:hours?|heures?|h)\s*(?:(?:a|per|par|/)\s*(?:day|jour|week|semaine)|daily|weekly|quotidiennes?|hebdomadaires?)\b'


def stated_pay(text): return list(re.finditer(PAY_PATTERN,text,re.I))
def stated_hours(text): return list(re.finditer(HOURS_PATTERN,text,re.I))


def short_day(match):
    if re.search(r'week|semaine|hebdomadaire',match.group(),re.I):return False
    words={'one':1,'two':2,'three':3,'four':4,'un':1,'une':1,'deux':2,'trois':3,'quatre':4}
    values=[words[x.lower()] if x.lower() in words else float(x.replace(',','.')) for x in match.groups() if x]
    return max(values)<=4


def parse_number(raw):
    text=''.join(str(unicodedata.decimal(c)) if c.isdecimal() else c for c in raw)
    scale=1000 if re.search(r'k\s*$',text,re.I) else 1
    text=re.sub(r"[\s'kK]",'',text).replace('٬',',').replace('٫','.')
    if ',' in text and '.' in text:
        decimal=',' if text.rfind(',')>text.rfind('.') else '.'
        group='.' if decimal==',' else ','
        text=text.replace(group,'').replace(decimal,'.')
    elif re.fullmatch(r'\d{1,3}(?:[,.]\d{3})+',text):
        text=text.replace(',','').replace('.','')
    else:text=text.replace(',','.')
    return float(text)*scale


def currency_code(raw):
    if re.search(r'TND|\bDT\b|tunisi|تونسي',raw,re.I):return 'TND'
    if re.search(r'DZD|alg[ée]ri',raw,re.I):return 'DZD'
    if re.search(r'EUR|euro|€',raw,re.I):return 'EUR'
    if re.search(r'GBP|sterling|£',raw,re.I):return 'GBP'
    for code in ('USD','CAD','MAD'):
        if re.search(code,raw,re.I):return code
    if re.search(r'dinar|دينار',raw,re.I):return 'DINAR_UNSPECIFIED'
    if re.search(r'dollar|\$',raw,re.I):return 'DOLLAR_UNSPECIFIED'
    if re.search(r'dirham',raw,re.I):return 'DIRHAM_UNSPECIFIED'
    return 'UNSPECIFIED'


def pay_details(text):
    result=[]
    for m in stated_pay(text):
        raw=m.group();numbers=[parse_number(n.group()) for n in re.finditer(NUMBER,raw)]
        if not numbers:continue
        prefix=text[max(0,m.start()-100):m.start()]
        fees=list(re.finditer(r'\b(?:frais|acompte|caution|deposit|fee|fees)\b',prefix,re.I))
        salary=list(re.finditer(r'\b(?:salary|salaire|r[ée]mun[ée]ration|earn|gagnez|compensation)\b',prefix,re.I))
        requested=bool(fees and (not salary or fees[-1].start()>salary[-1].start()))
        period=next((name for name,pattern in [('hour',r'hour|heure|ساعة'),('day',r'\bday|daily|jour|يوم'),('week',r'week|semaine'),('month',r'month|mois|mensuel|شهر'),('year',r'year|annual|annuel|ann[ée]e|\ban\b')] if re.search(pattern,raw,re.I)),None)
        result.append({'text':raw,'start':m.start(),'end':m.end(),'minimum':min(numbers),'maximum':max(numbers),'currency':currency_code(raw),'period':period,'kind':'requested_payment' if requested else 'compensation' if period or salary else 'unspecified_amount','currency_ambiguous':currency_code(raw).endswith('UNSPECIFIED')})
    return result
