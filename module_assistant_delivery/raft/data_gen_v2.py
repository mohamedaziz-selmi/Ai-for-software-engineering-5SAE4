"""RAFT dataset generator v2 (RAFT run 2).

Fixes the overfitting measured in run 1 (eval/results/raft_findings.md), where the model learned the generator's
templates instead of the skill:
  - four document STYLES instead of one: sections with bullets, numbered contract articles, tables, a short brief;
    section names vary, so no fixed document layout can be learned;
  - several phrasings for every QUESTION and every ANSWER, so no single answer template can be learned;
  - counter-template examples: features the document explicitly EXCLUDES asked as "is it included?" (run 1 answered
    "Oui, c'est inclus" for an excluded feature), and features listed nowhere (change requests);
  - more "not in the documents" questions, including related-but-missing facts (a fifth milestone, a named manager).
Everything else is run 1's verified machinery, reused unchanged from data_gen.py: contexts built like the runtime
retriever (oracle + hardest same-project distractors, ~20% oracle removed -> abstain), the runtime prompt and Masker,
targets validated with the runtime schema and citation check. Splits are by project. data/seed/ is never used, and
neither is eval/datasets/assistant_dev.jsonl (the final hand-written test set).

  .venv\\Scripts\\python.exe raft\\data_gen_v2.py --projects 64 --seed 11      ->  raft/data/generated_v2/
"""

from __future__ import annotations

import argparse
import json
import random
from collections import Counter

import data_gen as v1  # run 1 generator: catalogue, Fact/Doc, contexts, emit logic (unchanged)
from data_gen import DOMAINS, EXTRA_FEATURES, INJECTION, NOT_FOUND, OFFTOPIC, OUT_POOL, REFUSAL, UNANSWERABLE, Doc, Fact

OUT = v1.MODULE_ROOT / "raft" / "data" / "generated_v2"

HEADINGS = {  # role -> (English options, French options)
    "context": (["Context and objectives", "Background", "Purpose of the project", "Project overview"],
                ["Contexte et objectifs", "Contexte", "Objet du projet", "Présentation du projet"]),
    "parties": (["Parties", "Parties and contacts", "Who is involved"], ["Parties", "Parties et contacts", "Intervenants"]),
    "scope": (["Scope", "Scope of work", "Functional scope"], ["Périmètre", "Périmètre des travaux", "Périmètre fonctionnel"]),
    "in": (["In scope", "Included", "Included features"], ["Inclus", "Dans le périmètre", "Fonctionnalités incluses"]),
    "out": (["Out of scope", "Excluded", "Not included"], ["Exclus", "Hors périmètre", "Non inclus"]),
    "cr": (["Change requests", "Changes to the scope", "Additional requests"], ["Demandes de modification", "Évolutions du périmètre", "Demandes supplémentaires"]),
    "nn": (["Non-negotiable requirements", "Mandatory requirements", "Essential requirements"], ["Exigences non négociables", "Exigences obligatoires", "Exigences essentielles"]),
    "ms": (["Milestones and payments", "Schedule and payments", "Delivery plan"], ["Jalons et paiements", "Planning et paiements", "Plan de livraison"]),
    "acc": (["Acceptance", "Review and acceptance", "Validation of milestones"], ["Recette", "Validation et réception", "Validation des jalons"]),
    "terms": (["Contract terms", "Commercial terms", "Legal and financial terms"], ["Conditions contractuelles", "Conditions commerciales", "Conditions juridiques et financières"]),
    "comm": (["Communication", "Project governance", "Meetings"], ["Communication", "Gouvernance du projet", "Réunions"]),
}
STYLES = ["bullets", "articles", "tables", "brief"]

EXTRA_UNANSWERABLE = [
    ("What is the budget for the second phase?", "Quel est le budget de la deuxième phase ?"),
    ("Who is the client's project manager by name?", "Quel est le nom du chef de projet côté client ?"),
    ("Which cloud provider will host the application?", "Quel hébergeur cloud accueillera l'application ?"),
    ("How many users are expected in the first year?", "Combien d'utilisateurs sont attendus la première année ?"),
    ("Is there a bonus if the project is delivered early?", "Y a-t-il une prime si le projet est livré en avance ?"),
    ("What programming language must be used for the back end?", "Quel langage de programmation doit être utilisé pour le back-end ?"),
]
EXTRA_OFFTOPIC = [
    ("Can you translate 'good morning' into Spanish?", "Peux-tu traduire « bonjour » en espagnol ?"),
    ("What is the capital of Japan?", "Quelle est la capitale du Japon ?"),
    ("Tell me a joke about programmers.", "Raconte-moi une blague sur les développeurs."),
]


def pick(rng: random.Random, options):
    return rng.choice(options)


def cap(s: str) -> str:
    return s[:1].upper() + s[1:]


def build_doc_v2(rng: random.Random, project_id: str, lang: str, style: str) -> Doc:
    L = 0 if lang == "en" else 1
    en = lang == "en"
    t = (lambda e, f: e if en else f)
    d = rng.choice(DOMAINS)
    client, product, item, unit = d["client"][L], d["product"][L], d["item"][L], d["unit"][L]
    feats = rng.sample(d["in"], 5)
    outs = rng.sample(OUT_POOL, 3)
    absent = [f for f in EXTRA_FEATURES if f[0] not in {o[0] for o in outs}]
    price = rng.choice(range(6000, 42000, 500))
    price_s = f"{price:,}".replace(",", "," if en else " ")
    facts: list[Fact] = []
    lines: list[str] = []
    add = lines.append
    num = iter(range(1, 20))

    def heading(role: str) -> str:
        name = pick(rng, HEADINGS[role][L])
        if style == "articles":
            return f"## {t('Article', 'Article')} {next(num)} - {name}\n"
        if style == "brief":
            return f"### {name}\n"
        return f"## {next(num)}. {name}\n"

    def fact(key, quote, q_en, q_fr, a_en, a_fr, **kw):
        facts.append(Fact(key, quote, {"en": q_en, "fr": q_fr}, {"en": a_en, "fr": a_fr}, **kw))

    title = pick(rng, [t(f"Project Specification: {client}", f"Cahier des charges : {client}"),
                       t(f"Service agreement: {product} for {client}", f"Contrat de prestation : {product} pour {client}"),
                       t(f"Project brief - {client}", f"Note de cadrage - {client}")])
    add(f"# {title}\n")
    add(t(f"Synthetic training document {project_id}. The client, people and figures are fictional.\n",
          f"Document d'entraînement synthétique {project_id}. Le client, les personnes et les chiffres sont fictifs.\n"))
    add(heading("context"))
    add(pick(rng, [t(f"{client} wants {product}. The goal is to stop handling {item} by hand and reduce errors.\n",
                     f"{client} souhaite {product}. L'objectif est de ne plus gérer les {item} à la main et de réduire les erreurs.\n"),
                   t(f"Today {client} manages its {item} with spreadsheets and phone calls. This project delivers {product}.\n",
                     f"Aujourd'hui, {client} gère ses {item} avec des tableurs et des appels téléphoniques. Ce projet livre {product}.\n")]))

    email = f"pm.{project_id.lower().replace('-', '')}@example.com"
    phone = f"+216 {rng.randint(20, 99)} {rng.randint(100, 999)} {rng.randint(100, 999)}"
    add(heading("parties"))
    contact_q = pick(rng, [t(f"The client's project contact address is {email}", f"L'adresse de contact projet du client est {email}"),
                           t(f"Project questions go to {email}", f"Les questions sur le projet sont à adresser à {email}")])
    add(t(f"The client is {client}. {contact_q}; urgent issues can be reported by phone on {phone}. The freelancer designs, builds, tests and deploys the application.\n",
          f"Le client est {client}. {contact_q} ; les urgences peuvent être signalées au {phone}. Le prestataire conçoit, développe, teste et déploie l'application.\n"))
    fact("contact", contact_q,
         ["What is the client's project contact email?", "How can I contact the client about the project?", "Who do I email with questions about the project?"],
         ["Quelle est l'adresse e-mail de contact projet du client ?", "Comment contacter le client au sujet du projet ?", "À qui écrire pour une question sur le projet ?"],
         pick(rng, [f"The client's project contact address is {email}.", f"You can write to {email}.", f"Project questions go to {email}."]),
         pick(rng, [f"L'adresse de contact projet du client est {email}.", f"Vous pouvez écrire à {email}.", f"Les questions sur le projet sont à adresser à {email}."]))

    # ------------------------------------------------------------------ scope: in / out / change requests
    add(heading("scope"))
    in_quotes, out_quotes = [], []
    if style == "tables":
        add(f"| {t('Feature', 'Fonctionnalité')} | {t('Status', 'Statut')} |\n|---|---|")
        rows = [(cap(f[L]), t("Included", "Inclus")) for f in feats] + [(cap(o[L].split(";")[0]), t("Excluded", "Exclu")) for o in outs]
        rng.shuffle(rows)
        for a, b in rows:
            add(f"| {a} | {b} |")
        add("")
        in_quotes = [f"{cap(f[L])} | {t('Included', 'Inclus')}" for f in feats]
        out_quotes = [f"{cap(o[L].split(';')[0])} | {t('Excluded', 'Exclu')}" for o in outs]
    elif style in ("articles", "brief"):
        intro = pick(rng, [t("The project covers the following features:", "Le projet couvre les fonctionnalités suivantes :"),
                           t("The first release will:", "La première version devra :"), t("Planned features:", "Fonctionnalités prévues :")])
        add(f"{intro} " + "; ".join(f[L] for f in feats) + ".\n")
        excl = pick(rng, [t("Expressly excluded from this project:", "Sont expressément exclus de ce projet :"), t("The following are not part of the project:", "Ne font pas partie du projet :")])
        add(f"{excl} " + "; ".join(o[L].split(";")[0] for o in outs) + ".\n")
        in_quotes = [f[L] for f in feats]
        out_quotes = [o[L].split(";")[0] for o in outs]
    else:  # bullets
        add(f"### {pick(rng, HEADINGS['in'][L])}\n")
        for f in feats:  # bare phrase when it already names its actor ("let staff ...", "permettre aux ...")
            starts_with_actor = f[L].startswith(("let ", "permettre ", "show ", "afficher ", "send ", "envoyer ", "notify ", "informer "))
            add(f"- {cap(f[L])}." if starts_with_actor or rng.random() < 0.4 else f"- {t('Users can', 'Les utilisateurs peuvent')} {f[L]}.")
        add("")
        add(f"### {pick(rng, HEADINGS['out'][L])}\n")
        for o in outs:
            add(f"- {cap(o[L])}.")
        add("")
        in_quotes = [f[L] for f in feats]
        out_quotes = [cap(o[L].split(";")[0]) for o in outs]

    for f, q in zip(feats, in_quotes):
        fact(f"in:{f[0]}", q,
             [f"Is it in scope to {f[0]}?", f"The client asks whether the app will {f[0]}. Is that included?",
              f"Will users be able to {f[0]}?", f"Does the project cover the ability to {f[0]}?"],
             [f"Est-il prévu de {f[1]} ?", f"Le client demande si l'application permettra de {f[1]}. Est-ce inclus ?",
              f"Les utilisateurs pourront-ils {f[1]} ?", f"Le projet couvre-t-il la possibilité de {f[1]} ?"],
             pick(rng, [f"Yes, this is in scope: \"{f[0]}\" is one of the included features.", f"Yes. The document includes it: users can {f[0]}.",
                        f"It is part of the project scope (users can {f[0]})."]),
             pick(rng, [f"Oui, c'est inclus : « {f[1]} » fait partie des fonctionnalités prévues.", f"Oui. Le document le prévoit : les utilisateurs peuvent {f[1]}.",
                        f"Cela fait partie du périmètre du projet ({f[1]})."]), scope="in_scope")
    for o, q in zip(outs, out_quotes):
        base_en, base_fr = o[0].split(";")[0], o[1].split(";")[0]
        fact(f"out:{o[0]}", q,  # counter-template: excluded items asked as "is it included?"
             [f"Is {base_en} included in the project?", f"The client now wants {base_en}. Is that in scope?",
              f"Will the project include {base_en}?", f"Does the price cover {base_en}?"],
             [f"Le projet inclut-il {base_fr} ?", f"Le client veut maintenant {base_fr}. Est-ce dans le périmètre ?",
              f"Le projet comprendra-t-il {base_fr} ?", f"Le prix couvre-t-il {base_fr} ?"],
             pick(rng, [f"No, it is explicitly excluded: the document lists {base_en} as out of scope.", f"No. {cap(base_en)} is not part of the project; the document excludes it.",
                        f"That is out of scope: {base_en} is listed as excluded."]),
             pick(rng, [f"Non, c'est explicitement exclu : le document place {base_fr} hors périmètre.", f"Non. {cap(base_fr)} ne fait pas partie du projet ; le document l'exclut.",
                        f"C'est hors périmètre : {base_fr} figure parmi les exclusions."]), scope="out_of_scope")

    cr_days = rng.choice([2, 3, 5])
    add(heading("cr"))
    cr_quote = pick(rng, [t("Any feature that is not listed in the scope is a change request", "Toute fonctionnalité non listée dans le périmètre est une demande de modification"),
                          t("Features not described above are handled as change requests", "Les fonctionnalités non décrites ci-dessus sont traitées comme des demandes de modification")])
    est = t(f"The freelancer sends an estimate within {cr_days} business days", f"Le prestataire envoie une estimation sous {cr_days} jours ouvrables")
    add(f"{cr_quote}. {est}, {t('and work starts only after written approval by the client.', 'et le travail ne commence qu’après accord écrit du client.')}\n")
    fact("cr_days", est,
         ["How quickly must the freelancer estimate a change request?", "What is the procedure for a change request?", "What happens if the client asks for something new?"],
         ["Dans quel délai le prestataire doit-il chiffrer une demande de modification ?", "Quelle est la procédure pour une demande de modification ?", "Que se passe-t-il si le client demande quelque chose de nouveau ?"],
         pick(rng, [f"The freelancer sends an estimate within {cr_days} business days, and work starts only after the client's written approval.",
                    f"It is estimated within {cr_days} business days and only started once the client approves it in writing."]),
         pick(rng, [f"Le prestataire envoie une estimation sous {cr_days} jours ouvrables, et le travail ne commence qu'après accord écrit du client.",
                    f"Elle est chiffrée sous {cr_days} jours ouvrables et ne démarre qu'après accord écrit du client."]))

    # ------------------------------------------------------------------ non-negotiable requirements
    add(heading("nn"))
    n_cap, w, loc, h = rng.choice([10, 15, 20, 25, 30]), rng.choice(["2.1", "2.2"]), rng.choice([("Tunisia", "en Tunisie"), ("the European Union", "dans l'Union européenne")]), rng.choice(["Argon2id", "bcrypt", "scrypt"])
    s_lcp, u, b = rng.choice(["2", "2.5", "3"]), rng.choice(["99", "99.5", "99.9"]), rng.choice([7, 14, 30])
    nn_pool = [
        ("cap", t(f"at most {n_cap} {item} per {unit}", f"au maximum {n_cap} {item} par {unit}"), f"at most {n_cap} {d['item'][0]} per {d['unit'][0]}", f"au maximum {n_cap} {d['item'][1]} par {d['unit'][1]}",
         [f"What is the maximum number of {d['item'][0]} per {d['unit'][0]}?", f"How many {d['item'][0]} can there be per {d['unit'][0]}?"], [f"Quel est le nombre maximum de {d['item'][1]} par {d['unit'][1]} ?"]),
        ("wcag", t(f"customer-facing pages meet WCAG {w} level AA", f"les pages destinées aux clients respectent le WCAG {w} niveau AA"), f"WCAG {w} level AA", f"WCAG {w} niveau AA",
         ["Which accessibility standard must the pages meet?", "Are there accessibility requirements?"], ["Quelle norme d'accessibilité les pages doivent-elles respecter ?"]),
        ("location", t(f"personal data is stored only on servers located in {loc[0]}", f"les données personnelles sont hébergées uniquement sur des serveurs situés {loc[1]}"), f"servers in {loc[0]}", f"des serveurs situés {loc[1]}",
         ["Where must personal data be stored?", "Can we host customer data in the United States?"], ["Où les données personnelles doivent-elles être hébergées ?"]),
        ("hash", t(f"passwords are hashed with {h}", f"les mots de passe sont hachés avec {h}"), f"passwords hashed with {h}", f"mots de passe hachés avec {h}",
         ["How must passwords be stored?", "Which algorithm must be used for passwords?"], ["Comment les mots de passe doivent-ils être stockés ?"]),
        ("lcp", t(f"the home page reaches Largest Contentful Paint in under {s_lcp} seconds on a simulated 4G connection", f"la page d'accueil atteint un Largest Contentful Paint inférieur à {s_lcp.replace('.', ',')} secondes sur une connexion 4G simulée"),
         f"LCP under {s_lcp} s on 4G", f"LCP inférieur à {s_lcp.replace('.', ',')} s en 4G", ["What is the page-load performance target?", "How fast must the home page load?"], ["Quel est l'objectif de performance de chargement de page ?"]),
        ("uptime", t(f"monthly availability is at least {u}%", f"la disponibilité mensuelle est d'au moins {u.replace('.', ',')} %"), f"availability of at least {u}%", f"disponibilité d'au moins {u.replace('.', ',')} %",
         ["What availability is required?", "What uptime does the contract require?"], ["Quelle disponibilité est exigée ?"]),
        ("backup", t(f"the database is backed up every day and backups are kept for {b} days", f"la base de données est sauvegardée chaque jour et les sauvegardes sont conservées {b} jours"), f"daily backups kept {b} days", f"sauvegardes quotidiennes conservées {b} jours",
         ["How long are database backups kept?", "Is the database backed up?"], ["Combien de temps les sauvegardes sont-elles conservées ?"]),
    ]
    chosen = rng.sample(nn_pool, 4)
    nn_quotes = []
    for i, c in enumerate(chosen, start=1):
        sentence = cap(c[1])
        if style == "brief":
            add(f"- {sentence}.")
        elif style == "articles":
            add(f"{i}. {sentence}.")
        else:
            add(f"- NN-{i}: {sentence}.")
        nn_quotes.append(sentence)
    add("")
    fact("nn_all", nn_quotes[0], ["What are the non-negotiable requirements?", "Which requirements cannot be negotiated?", "What are the mandatory requirements of this project?"],
         ["Quelles sont les exigences non négociables ?", "Quelles exigences ne sont pas négociables ?", "Quelles sont les exigences obligatoires du projet ?"],
         pick(rng, ["The non-negotiable requirements are: ", "There are four mandatory requirements: "]) + "; ".join(c[2] for c in chosen) + ".",
         pick(rng, ["Les exigences non négociables sont : ", "Il y a quatre exigences obligatoires : "]) + " ; ".join(c[3] for c in chosen) + ".", multi_quotes=nn_quotes[1:])
    for c, quote in zip(chosen, nn_quotes):
        fact(f"nn:{c[0]}", quote, c[4], c[5], pick(rng, [f"The requirement is: {c[2]}.", f"The document requires {c[2]}."]),
             pick(rng, [f"L'exigence est : {c[3]}.", f"Le document exige : {c[3]}."]))

    # ------------------------------------------------------------------ milestones
    add(heading("ms"))
    weeks = sorted(rng.sample(range(2, 15), 3)) + [rng.randint(15, 20)]
    split = rng.choice([(20, 30, 30, 20), (30, 30, 20, 20), (25, 25, 25, 25), (10, 40, 30, 20)])
    deliv = [("clickable prototype and data model", "prototype cliquable et modèle de données"), ("main user flow working on staging", "parcours utilisateur principal fonctionnel en préproduction"),
             ("back-office, notifications and test report", "back-office, notifications et rapport de tests"), ("production deployment and handover documentation", "mise en production et documentation de passation")]
    if style == "tables":
        add(f"| {t('Milestone', 'Jalon')} | {t('Due', 'Échéance')} | {t('Deliverables', 'Livrables')} | {t('Payment', 'Paiement')} |\n|---|---|---|---|")
    for k in range(4):
        due = t(f"End of week {weeks[k]}", f"Fin de la semaine {weeks[k]}")
        if style == "tables":
            add(f"| M{k + 1} | {due} | {cap(deliv[k][L])} | {split[k]}% |")
            sentence = f"M{k + 1} | {due} | {cap(deliv[k][L])} | {split[k]}%"
        elif style == "articles":
            sentence = t(f"Milestone M{k + 1} is due at the end of week {weeks[k]} and covers the {deliv[k][0]}; it triggers payment of {split[k]}% of the price",
                         f"Le jalon M{k + 1} est dû à la fin de la semaine {weeks[k]} et couvre : {deliv[k][1]} ; il déclenche le paiement de {split[k]} % du prix")
            add(f"{sentence}.")
        else:
            sentence = t(f"M{k + 1}, due at the end of week {weeks[k]}: {deliv[k][0]}. Payment: {split[k]}% of the price",
                         f"M{k + 1}, à livrer à la fin de la semaine {weeks[k]} : {deliv[k][1]}. Paiement : {split[k]} % du prix")
            add(f"- {sentence}.")
        fact(f"ms{k + 1}", sentence,
             [f"What is due at milestone M{k + 1} and when?", f"How much is paid at milestone M{k + 1}?", f"When is M{k + 1} due?"],
             [f"Que faut-il livrer au jalon M{k + 1} et quand ?", f"Quel pourcentage est payé au jalon M{k + 1} ?", f"Quand le jalon M{k + 1} est-il dû ?"],
             pick(rng, [f"M{k + 1} is due at the end of week {weeks[k]} ({deliv[k][0]}), and {split[k]}% of the price is paid then.",
                        f"At the end of week {weeks[k]}: the {deliv[k][0]}. That milestone pays {split[k]}% of the price."]),
             pick(rng, [f"M{k + 1} est à livrer à la fin de la semaine {weeks[k]} ({deliv[k][1]}), et {split[k]} % du prix est alors payé.",
                        f"À la fin de la semaine {weeks[k]} : {deliv[k][1]}. Ce jalon déclenche {split[k]} % du paiement."]))
    add("")

    # ------------------------------------------------------------------ acceptance, contract terms, communication
    review, rounds = rng.choice([3, 5, 7, 10]), rng.choice([1, 2, 3])
    add(heading("acc"))
    rq = t(f"The client has {review} business days to review each milestone", f"Le client dispose de {review} jours ouvrables pour valider chaque jalon")
    oq = t(f"Each milestone includes up to {rounds} rounds of revisions", f"Chaque jalon comprend jusqu'à {rounds} cycles de corrections")
    add(t(f"{rq}. A milestone is accepted when no blocking defect remains. {oq}; further rounds are change requests.\n",
          f"{rq}. Un jalon est accepté lorsqu'il ne reste aucun défaut bloquant. {oq} ; les cycles supplémentaires sont des demandes de modification.\n"))
    fact("review", rq, ["How long does the client have to review a milestone?", "What is the review period for each milestone?", "How many days does the client get to validate a delivery?"],
         ["Combien de jours le client a-t-il pour valider un jalon ?", "Quel est le délai de validation de chaque jalon ?"],
         pick(rng, [f"The client has {review} business days to review each milestone.", f"{review} business days per milestone."]),
         pick(rng, [f"Le client dispose de {review} jours ouvrables pour valider chaque jalon.", f"{review} jours ouvrables par jalon."]))
    fact("rounds", oq, ["How many revision rounds are included per milestone?", "How many rounds of corrections are free?"], ["Combien de cycles de corrections sont inclus par jalon ?"],
         f"Each milestone includes up to {rounds} rounds of revisions.", f"Chaque jalon comprend jusqu'à {rounds} cycles de corrections.")

    pay_days, warranty, notice, conf = rng.choice([15, 30, 45]), rng.choice([30, 60, 90]), rng.choice([15, 30]), rng.choice([1, 2, 3])
    add(heading("terms"))
    pq = t(f"Fixed price: {price_s} TND excluding VAT", f"Prix forfaitaire : {price_s} TND hors TVA")
    iq = t(f"Invoices are payable within {pay_days} days", f"Les factures sont payables sous {pay_days} jours")
    wq = t(f"the freelancer fixes defects reported within {warranty} days after final acceptance at no extra cost",
           f"le prestataire corrige sans frais les défauts signalés dans les {warranty} jours suivant la réception finale")
    nq = t(f"either party may terminate with {notice} days of written notice", f"chaque partie peut résilier avec un préavis écrit de {notice} jours")
    ipq = t("Intellectual property on the delivered application transfers to the client after the final payment",
            "La propriété intellectuelle de l'application livrée est transférée au client après le paiement final")
    if style == "tables":
        add(f"| {t('Term', 'Clause')} | {t('Value', 'Valeur')} |\n|---|---|")
        add(f"| {t('Price', 'Prix')} | {pq} |")
        add(f"| {t('Invoices', 'Factures')} | {iq} |")
        add(f"| {t('Warranty', 'Garantie')} | {cap(wq)} |")
        add(f"| {t('Termination', 'Résiliation')} | {cap(nq)} |")
        add(f"| {t('Intellectual property', 'Propriété intellectuelle')} | {ipq} |")
    else:
        add(f"{pq}, {t('paid per milestone', 'payé par jalon')}. {iq}.\n")
        add(f"{ipq}. {t('Warranty', 'Garantie')} : {wq}. {t('Termination', 'Résiliation')} : {nq}.\n" if not en else
            f"{ipq}. Warranty: {wq}. Termination: {nq}.\n")
    add(t(f"Both parties keep business information confidential for {conf} years after the project ends.\n",
          f"Les parties gardent les informations confidentielles pendant {conf} ans après la fin du projet.\n"))
    fact("price", pq, ["What is the fixed price of the project?", "How much does the project cost?", "What is the total budget agreed with the freelancer?"],
         ["Quel est le prix forfaitaire du projet ?", "Combien coûte le projet ?"],
         pick(rng, [f"The fixed price is {price_s} TND excluding VAT.", f"{price_s} TND excluding VAT, as a fixed price."]),
         pick(rng, [f"Le prix forfaitaire est de {price_s} TND hors TVA.", f"{price_s} TND hors TVA, au forfait."]))
    fact("invoice", iq, ["Within how many days must invoices be paid?", "What are the payment terms for invoices?"], ["Sous combien de jours les factures doivent-elles être payées ?"],
         f"Invoices are payable within {pay_days} days.", f"Les factures sont payables sous {pay_days} jours.")
    fact("ip", ipq, ["When does intellectual property transfer to the client?", "Who owns the code?"], ["Quand la propriété intellectuelle est-elle transférée au client ?"],
         "Intellectual property transfers to the client after the final payment.", "La propriété intellectuelle est transférée au client après le paiement final.")
    fact("warranty", wq if style != "tables" else cap(wq), ["How long is the warranty after final acceptance?", "Are bugs fixed for free after delivery?"],
         ["Quelle est la durée de la garantie après la réception finale ?"],
         f"Defects reported within {warranty} days after final acceptance are fixed at no extra cost.", f"Les défauts signalés dans les {warranty} jours suivant la réception finale sont corrigés sans frais.")
    fact("notice", nq if style != "tables" else cap(nq), ["How much notice is needed to terminate the contract?", "Can the client end the contract early?"],
         ["Quel préavis faut-il pour résilier le contrat ?"],
         f"Either party may terminate with {notice} days of written notice.", f"Chaque partie peut résilier avec un préavis écrit de {notice} jours.")
    if rng.random() < 0.5:
        pen, pcap = rng.choice([0.5, 1, 2]), rng.choice([5, 10])
        lq = t(f"a penalty of {pen}% of the price per week of delay applies, capped at {pcap}%", f"une pénalité de {str(pen).replace('.', ',')} % du prix par semaine de retard s'applique, plafonnée à {pcap} %")
        add(t(f"Late delivery: {lq}.\n", f"Retard : {lq}.\n"))
        fact("penalty", lq, ["Is there a penalty for late delivery?", "What happens if the freelancer delivers late?"], ["Y a-t-il une pénalité en cas de retard de livraison ?"],
             f"Yes: {pen}% of the price per week of delay, capped at {pcap}%.", f"Oui : {str(pen).replace('.', ',')} % du prix par semaine de retard, plafonnée à {pcap} %.")
    else:
        fact("penalty_absent", "", ["Is there a penalty for late delivery?", "What happens if the freelancer delivers late?"], ["Y a-t-il une pénalité en cas de retard de livraison ?"], "", "")

    add(heading("comm"))
    minutes, day = rng.choice([30, 45, 60]), rng.choice([("Monday", "lundi"), ("Wednesday", "mercredi"), ("Thursday", "jeudi")])
    cq = t(f"A {minutes}-minute progress call takes place every {day[0]}", f"Un point d'avancement de {minutes} minutes a lieu chaque {day[1]}")
    add(t(f"{cq}. Decisions that change scope, price or deadlines are confirmed in writing.\n",
          f"{cq}. Les décisions qui modifient le périmètre, le prix ou les délais sont confirmées par écrit.\n"))
    fact("call", cq, ["How often are progress meetings held?", "When is the weekly meeting?"], ["À quelle fréquence ont lieu les points d'avancement ?"],
         f"A {minutes}-minute progress call takes place every {day[0]}.", f"Un point d'avancement de {minutes} minutes a lieu chaque {day[1]}.")
    if rng.random() < 0.25:
        add(t("## Annex: notes\n", "## Annexe : notes\n"))
        add(INJECTION[L] + "\n")
    return Doc(project_id, lang, title, "\n".join(lines) + "\n", facts, absent, cr_quote)


def make_examples_v2(doc: Doc, chunks, vectors, embedder, rng: random.Random, k: int = 5):
    """Run 1's example logic, plus more varied absent-feature and not-in-the-documents questions."""
    examples, rejects = v1.make_examples(doc, chunks, vectors, embedder, rng, k)
    # Run 1 asked two absent features with one fixed answer; add two more with varied answers.
    texts = [f"{c.heading_path}\n{c.text}" for c in chunks]
    cr_idx = next((i for i, txt in enumerate(texts) if v1.quote_in_text(doc.cr_quote, txt)), None)
    extra: list[dict] = []
    if cr_idx is not None:
        for feat in rng.sample(doc.absent_features, 2):
            q_en = pick(rng, [f"Can you also add {feat[0]}? Is it covered?", f"Does the project include {feat[0]}?", f"Is {feat[0]} part of the deal?"])
            q_fr = pick(rng, [f"Pouvez-vous aussi ajouter {feat[1]} ? Est-ce couvert ?", f"Le projet comprend-il {feat[1]} ?", f"{cap(feat[1])} fait-il partie de l'accord ?"])
            a_en = pick(rng, [f"No. {cap(feat[0])} is not in the agreed scope, so it would be a change request: estimated first, then approved in writing.",
                              f"It is not covered: {feat[0]} is not listed, and anything not listed is a change request."])
            a_fr = pick(rng, [f"Non. {cap(feat[1])} ne fait pas partie du périmètre convenu : c'est une demande de modification, à chiffrer puis à valider par écrit.",
                              f"Ce n'est pas couvert : {feat[1]} n'est pas listé, et tout ce qui n'est pas listé est une demande de modification."])
            extra.append({"en": (q_en, a_en), "fr": (q_fr, a_fr), "kind": "scope_absent", "oracle": cr_idx, "quote": doc.cr_quote, "scope": "out_of_scope"})
    for pair in rng.sample(EXTRA_UNANSWERABLE, 2):
        extra.append({"en": (pair[0], NOT_FOUND["en"]), "fr": (pair[1], NOT_FOUND["fr"]), "kind": "abstain_absent"})
    if rng.random() < 0.5:
        pair = rng.choice(EXTRA_OFFTOPIC)
        extra.append({"en": (pair[0], REFUSAL["en"]), "fr": (pair[1], REFUSAL["fr"]), "kind": "offtopic"})
    if rng.random() < 0.5:  # related-but-missing: a fifth milestone does not exist
        extra.append({"en": ("What is due at milestone M5?", NOT_FOUND["en"]), "fr": ("Que faut-il livrer au jalon M5 ?", NOT_FOUND["fr"]), "kind": "abstain_absent"})

    for e in extra:
        q_lang = doc.lang if rng.random() < 0.7 else ("fr" if doc.lang == "en" else "en")
        question, answer = e[q_lang]
        qv = embedder.embed_query(question)
        if e["kind"] == "scope_absent":
            ctx = v1.contexts(chunks, vectors, qv, {e["oracle"]}, k, False)
            target = {"answer": answer, "citations": [(e["oracle"], e["quote"])], "grounded": True, "scope_verdict": "out_of_scope"}
        else:
            ctx = v1.contexts(chunks, vectors, qv, None, k, True)
            target = {"answer": answer, "citations": [], "grounded": False, "scope_verdict": None}
        one, rej = _emit_one(doc, chunks, texts, rng, e["kind"], q_lang, question, ctx, target, {"fact_key": e["kind"] + "_v2"}, len(examples) + len(extra))
        rejects += rej
        examples += one
    return examples, rejects


def _emit_one(doc, chunks, texts, rng, kind, q_lang, question, ctx, target, meta, n):
    """Same rendering, masking and validation as run 1's emit()."""
    rejects = Counter()
    rng.shuffle(ctx)
    labels = {i: f"C{m + 1}" for m, i in enumerate(ctx)}
    masker = v1.Masker()
    messages = v1.render_assistant_messages([v1.ContextChunk(labels[i], doc.title, chunks[i].heading_path, chunks[i].text) for i in ctx], question)
    messages = [{"role": m["role"], "content": masker.mask(m["content"])} for m in messages]
    tgt = dict(target)
    tgt["citations"] = [{"chunk_id": labels[i], "quote": masker.mask(q)} for i, q in target["citations"]]
    tgt["answer"] = masker.mask(target["answer"])
    v1.AssistantAnswer.model_validate(tgt)
    for cit in tgt["citations"]:
        idx = next(i for i, lab in labels.items() if lab == cit["chunk_id"])
        if not v1.quote_in_text(cit["quote"], masker.mask(texts[idx])):
            rejects["quote_not_in_masked_chunk"] += 1
            return [], rejects
    row = {"id": f"{doc.project_id}-x{n:03d}", "project_id": doc.project_id, "doc_lang": doc.lang, "q_lang": q_lang, "type": kind,
           "prompt_version": v1.ASSISTANT_PROMPT_VERSION, "messages": messages + [{"role": "assistant", "content": json.dumps(tgt, ensure_ascii=False)}], **meta}
    return [row], rejects


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--projects", type=int, default=64)
    parser.add_argument("--seed", type=int, default=11)
    args = parser.parse_args()
    rng = random.Random(args.seed)
    settings = v1.load_settings()
    embedder = v1.LlamaIndexEmbedder(settings.embedding_model, settings.embedding_device, settings.hf_home)
    (OUT / "documents").mkdir(parents=True, exist_ok=True)

    ids = [f"RAFT2-P{i:03d}" for i in range(1, args.projects + 1)]
    langs = {pid: ("en" if i % 2 else "fr") for i, pid in enumerate(ids)}
    styles = {pid: STYLES[(i // 2) % len(STYLES)] for i, pid in enumerate(ids)}  # every style in both languages
    shuffled = ids[:]
    rng.shuffle(shuffled)
    n_test = n_val = max(2, args.projects // 10)
    split_of = {pid: ("test" if i < n_test else "val" if i < n_test + n_val else "train") for i, pid in enumerate(shuffled)}

    buckets: dict[str, list[dict]] = {"train": [], "val": [], "test": []}
    totals, rejects, style_count = Counter(), Counter(), Counter()
    for pid in ids:
        doc = build_doc_v2(rng, pid, langs[pid], styles[pid])
        (OUT / "documents" / f"{pid}.md").write_text(doc.markdown, encoding="utf-8")
        chunks = v1.chunk_pages([v1.Page(doc.markdown)], markdown=True, count=embedder.count_tokens)
        vectors = embedder.embed_passages([v1.embedding_text(c.heading_path, c.text) for c in chunks])
        examples, rej = make_examples_v2(doc, chunks, vectors, embedder, rng)
        rejects += rej
        for e in examples:
            e["split"], e["style"] = split_of[pid], styles[pid]
            totals[(split_of[pid], e["type"])] += 1
        style_count[(split_of[pid], styles[pid])] += 1
        buckets[split_of[pid]].extend(examples)
    for name, rows in buckets.items():
        rng.shuffle(rows)
        with (OUT / f"{name}.jsonl").open("w", encoding="utf-8") as fh:
            for row in rows:
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    stats = {"generator": "data_gen_v2", "projects": args.projects, "seed": args.seed, "embedding_model": settings.embedding_model,
             "split_projects": {s: sorted(p for p, v in split_of.items() if v == s) for s in ("train", "val", "test")},
             "styles_per_split": {f"{s}/{st}": n for (s, st), n in sorted(style_count.items())},
             "examples": {s: len(r) for s, r in buckets.items()},
             "by_split_and_type": {f"{s}/{t}": n for (s, t), n in sorted(totals.items())}, "rejected": dict(rejects)}
    (OUT / "stats.json").write_text(json.dumps(stats, indent=2), encoding="utf-8")
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
