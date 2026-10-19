# Contrat de prestation : un portail de réservation de location de voitures pour Rent&Go Sfax

Document d'entraînement synthétique RAFT2-P005. Le client, les personnes et les chiffres sont fictifs.

## 1. Contexte et objectifs

Aujourd'hui, Rent&Go Sfax gère ses réservations avec des tableurs et des appels téléphoniques. Ce projet livre un portail de réservation de location de voitures.

## 2. Parties et contacts

Le client est Rent&Go Sfax. Les questions sur le projet sont à adresser à pm.raft2p005@example.com ; les urgences peuvent être signalées au +216 83 161 601. Le prestataire conçoit, développe, teste et déploie l'application.

## 3. Périmètre fonctionnel

| Fonctionnalité | Statut |
|---|---|
| Téléverser une copie du permis de conduire | Inclus |
| Réserver une voiture et choisir l'agence de retrait | Inclus |
| La tarification multi-devises | Exclu |
| La livraison à domicile | Exclu |
| Permettre aux agents de confirmer ou refuser les réservations | Inclus |
| Le paiement en ligne par carte  | Exclu |
| Envoyer un e-mail de confirmation avec le numéro de réservation | Inclus |
| Rechercher les voitures disponibles par date et catégorie | Inclus |

## 4. Demandes de modification

Les fonctionnalités non décrites ci-dessus sont traitées comme des demandes de modification. Le prestataire envoie une estimation sous 5 jours ouvrables, et le travail ne commence qu’après accord écrit du client.

## 5. Exigences non négociables

- NN-1: Les mots de passe sont hachés avec bcrypt.
- NN-2: La disponibilité mensuelle est d'au moins 99,9 %.
- NN-3: Les données personnelles sont hébergées uniquement sur des serveurs situés en Tunisie.
- NN-4: La page d'accueil atteint un Largest Contentful Paint inférieur à 2,5 secondes sur une connexion 4G simulée.

## 6. Planning et paiements

| Jalon | Échéance | Livrables | Paiement |
|---|---|---|---|
| M1 | Fin de la semaine 7 | Prototype cliquable et modèle de données | 30% |
| M2 | Fin de la semaine 11 | Parcours utilisateur principal fonctionnel en préproduction | 30% |
| M3 | Fin de la semaine 13 | Back-office, notifications et rapport de tests | 20% |
| M4 | Fin de la semaine 15 | Mise en production et documentation de passation | 20% |

## 7. Validation et réception

Le client dispose de 10 jours ouvrables pour valider chaque jalon. Un jalon est accepté lorsqu'il ne reste aucun défaut bloquant. Chaque jalon comprend jusqu'à 2 cycles de corrections ; les cycles supplémentaires sont des demandes de modification.

## 8. Conditions commerciales

| Clause | Valeur |
|---|---|
| Prix | Prix forfaitaire : 11 500 TND hors TVA |
| Factures | Les factures sont payables sous 45 jours |
| Garantie | Le prestataire corrige sans frais les défauts signalés dans les 90 jours suivant la réception finale |
| Résiliation | Chaque partie peut résilier avec un préavis écrit de 30 jours |
| Propriété intellectuelle | La propriété intellectuelle de l'application livrée est transférée au client après le paiement final |
Les parties gardent les informations confidentielles pendant 2 ans après la fin du projet.

## 9. Communication

Un point d'avancement de 60 minutes a lieu chaque lundi. Les décisions qui modifient le périmètre, le prix ou les délais sont confirmées par écrit.

