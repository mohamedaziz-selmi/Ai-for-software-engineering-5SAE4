# Contrat de prestation : une plateforme d'inscription aux cours pour École de langues Dar Lughat

Document d'entraînement synthétique RAFT2-P041. Le client, les personnes et les chiffres sont fictifs.

## 1. Contexte

École de langues Dar Lughat souhaite une plateforme d'inscription aux cours. L'objectif est de ne plus gérer les inscriptions à la main et de réduire les erreurs.

## 2. Intervenants

Le client est École de langues Dar Lughat. L'adresse de contact projet du client est pm.raft2p041@example.com ; les urgences peuvent être signalées au +216 45 365 948. Le prestataire conçoit, développe, teste et déploie l'application.

## 3. Périmètre

### Fonctionnalités incluses

- Les utilisateurs peuvent parcourir les cours par langue et niveau.
- Permettre aux enseignants de saisir les présences.
- Les utilisateurs peuvent passer un test de niveau en ligne.
- Permettre au personnel de gérer les groupes et les salles.
- Les utilisateurs peuvent s'inscrire dans un groupe de cours.

### Hors périmètre

- La migration des données historiques.
- Le paiement en ligne par carte ; les clients paient sur place.
- Un programme de fidélité.

## 4. Évolutions du périmètre

Toute fonctionnalité non listée dans le périmètre est une demande de modification. Le prestataire envoie une estimation sous 3 jours ouvrables, et le travail ne commence qu’après accord écrit du client.

## 5. Exigences obligatoires

- NN-1: Les mots de passe sont hachés avec bcrypt.
- NN-2: Au maximum 10 inscriptions par groupe de cours.
- NN-3: La page d'accueil atteint un Largest Contentful Paint inférieur à 3 secondes sur une connexion 4G simulée.
- NN-4: Les pages destinées aux clients respectent le WCAG 2.1 niveau AA.

## 6. Planning et paiements

- M1, à livrer à la fin de la semaine 8 : prototype cliquable et modèle de données. Paiement : 30 % du prix.
- M2, à livrer à la fin de la semaine 9 : parcours utilisateur principal fonctionnel en préproduction. Paiement : 30 % du prix.
- M3, à livrer à la fin de la semaine 10 : back-office, notifications et rapport de tests. Paiement : 20 % du prix.
- M4, à livrer à la fin de la semaine 17 : mise en production et documentation de passation. Paiement : 20 % du prix.

## 7. Validation des jalons

Le client dispose de 10 jours ouvrables pour valider chaque jalon. Un jalon est accepté lorsqu'il ne reste aucun défaut bloquant. Chaque jalon comprend jusqu'à 2 cycles de corrections ; les cycles supplémentaires sont des demandes de modification.

## 8. Conditions commerciales

Prix forfaitaire : 13 500 TND hors TVA, payé par jalon. Les factures sont payables sous 30 jours.

La propriété intellectuelle de l'application livrée est transférée au client après le paiement final. Garantie : le prestataire corrige sans frais les défauts signalés dans les 90 jours suivant la réception finale. Résiliation : chaque partie peut résilier avec un préavis écrit de 30 jours.

Les parties gardent les informations confidentielles pendant 1 ans après la fin du projet.

Retard : une pénalité de 1 % du prix par semaine de retard s'applique, plafonnée à 10 %.

## 9. Gouvernance du projet

Un point d'avancement de 60 minutes a lieu chaque mercredi. Les décisions qui modifient le périmètre, le prix ou les délais sont confirmées par écrit.

