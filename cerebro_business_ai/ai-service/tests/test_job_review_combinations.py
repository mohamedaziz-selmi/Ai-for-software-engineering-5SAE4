from pathlib import Path
import pytest
from services.job_review import Posting, review, stated_pay, stated_hours
from services.smart_intake import fraud_intake
from app.resource_guard import ResourceGuard, ResourceLimits


@pytest.fixture
def rule_review(monkeypatch):
    # Rules must detect the combination even if a classifier is unconvinced.
    class FixedClassifier:
        def predict_proba(self, rows): return [[.59,.41] for _ in rows]
    monkeypatch.setattr('app.main.load_real_fraud_model',lambda:FixedClassifier())
    monkeypatch.setattr('services.job_review.ResourceGuard',lambda:ResourceGuard(ResourceLimits(sample_interval_seconds=.01)))
    return lambda text:review(Posting(text=text))


def test_brightpath_combination_requires_investigation_even_below_fifty(rule_review):
    text=(Path(__file__).resolve().parents[2]/'data/reliability_review/brightpath.txt').read_text(encoding='utf-8')
    result=rule_review(text)
    assert result['model_probability']==.41
    assert result['risk_tier']=='high'
    assert result['advisory']=='Investigate before proceeding'
    assert result['extracted']['pay']==['9,000 to 12,000 TND per month']
    assert result['extracted']['hours']==['3 to 4 hours a day']
    for item in result['evidence']: assert text[item['start']:item['end']]==item['text']
    assert any(e['category']=='Compensation, short days and minimal requirements' for e in result['evidence'])


@pytest.mark.parametrize('text',[
    'Senior Frontend Developer, urgent hiring. Full-time, 40 hours per week, React TypeScript accessibility testing. Five years experience required. Salary 9000 to 12000 TND per month. Apply on careers.example.com.',
    'Junior Frontend Developer. No experience required. Full-time 40 hours per week. Learn React TypeScript HTML CSS and Git with mentoring. Salary 1800 to 2400 TND per month. A technical interview is required.',
    'Part-time Frontend Developer. React and CSS required. Work 3 to 4 hours a day. Salary 2500 TND per month. A technical test and interview are required.',
    'Part-time library assistant. No experience required. Work 3 to 4 hours a day. Pay $15 per hour. Sort books, welcome visitors and help with shelving under supervision. Apply to the library and attend an interview.',
])
def test_salary_urgency_or_entry_level_alone_does_not_trigger_combined_high_risk(rule_review,text):
    result=rule_review(text)
    assert result['risk_tier']!='high'
    assert not any(e['category']=='Compensation, short days and minimal requirements' for e in result['evidence'])


def test_french_currency_and_hours_are_shared_with_intake():
    text='Développeur web sans expérience, 9 000 à 12 000 DT par mois. Travail 3 à 4 heures par jour.'
    assert len(stated_pay(text))==1
    assert len(stated_hours(text))==1
    result=fraud_intake(text)
    assert result['fields']['compensation'][0]['value']=='9 000 à 12 000 DT par mois'


def test_negated_application_payment_is_not_a_request(rule_review):
    result=rule_review('Junior frontend developer. React and TypeScript are required. We never ask you to pay a registration fee. There is no application fee. A technical interview is required.')
    assert not any(e['category']=='Upfront payment' for e in result['evidence'])


def test_actual_payment_request_remains_high(rule_review):
    result=rule_review('Remote assistant vacancy. Pay a registration fee to complete your application and contact Telegram for an immediate interview.')
    assert result['risk_tier']=='high'
    assert any(e['category']=='Upfront payment' for e in result['evidence'])


@pytest.mark.parametrize('text,category',[
    ('Assistant à distance sans expérience. Gagnez 3000 euros par mois pour 2h/jour. Payez des frais de dossier avant de commencer. Contactez WhatsApp.', 'Upfront payment'),
    ('Développeur web débutants acceptés. Temps plein, 3 à 4 heures par jour, 9000 dinars par mois, salaire exceptionnel. Contact Telegram.', 'Compensation, short days and minimal requirements'),
    ('Remote assistant. Guaranteed hiring, no interview required. Contact us only on Telegram to receive your contract.', 'Hiring bypassed through informal contact'),
    ('Remote assistant role. Please send your account password and OTP to the recruiter to activate your payroll account.', 'Credentials or verification codes requested'),
    ('Assistant à distance. Communiquez votre mot de passe et votre code de vérification au recruteur avant le contrat.', 'Credentials or verification codes requested'),
    ('We will send a cheque for your laptop. Deposit the cheque and return the difference to our agent before your first day.', 'Cheque and onward-payment arrangement'),
])
def test_bilingual_scam_patterns_have_exact_evidence(rule_review,text,category):
    result=rule_review(text)
    assert result['risk_tier']=='high'
    assert any(e['category']==category for e in result['evidence'])
    for e in result['evidence']:assert text[e['start']:e['end']]==e['text']


@pytest.mark.parametrize('text',[
    'Développeur React confirmé, salaire 3000 euros par mois. Aucun frais de dossier. Entretien technique et contrat avant prise de poste.',
    'Assistant débutant, salaire 1800 dinars tunisiens par mois, 40 heures par semaine. Sans frais de candidature. Entretien au bureau.',
    'Backend developer for bank account APIs. Implement secure transaction processing with Java and SQL. Five years experience, technical interview and references required.',
    'Security engineer. We never ask you to share your password. Implement TypeScript login pages and write tests for our team.',
    'Développeur React. Ne communiquez jamais votre mot de passe. Nous ne demandons jamais de frais de dossier. Entretien technique et contrat obligatoires.',
    'Frontend developer. We never charge an application fee. We do not require a registration fee. React, TypeScript and a technical interview are required.',
])
def test_currency_and_domain_vocabulary_do_not_create_payment_or_credential_requests(rule_review,text):
    result=rule_review(text)
    assert not any(e['category'] in ('Upfront payment','Financial information','Credentials or verification codes requested') for e in result['evidence'])
