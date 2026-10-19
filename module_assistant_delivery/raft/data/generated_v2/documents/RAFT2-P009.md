# Cahier des charges : Rent&Go Sfax

Document d'entraînement synthétique RAFT2-P009. Le client, les personnes et les chiffres sont fictifs.

## 1. Contexte et objectifs

Rent&Go Sfax souhaite un portail de réservation de location de voitures. L'objectif est de ne plus gérer les réservations à la main et de réduire les erreurs.

## 2. Intervenants

Le client est Rent&Go Sfax. L'adresse de contact projet du client est pm.raft2p009@example.com ; les urgences peuvent être signalées au +216 94 432 929. Le prestataire conçoit, développe, teste et déploie l'application.

## 3. Périmètre des travaux

### Fonctionnalités incluses

- Envoyer un e-mail de confirmation avec le numéro de réservation.
- Les utilisateurs peuvent téléverser une copie du permis de conduire.
- Afficher au personnel un calendrier de disponibilité de la flotte.
- Permettre aux agents de confirmer ou refuser les réservations.
- Réserver une voiture et choisir l'agence de retrait.

### Non inclus

- La livraison à domicile.
- La tarification multi-devises.
- La migration des données historiques.

## 4. Évolutions du périmètre

Les fonctionnalités non décrites ci-dessus sont traitées comme des demandes de modification. Le prestataire envoie une estimation sous 2 jours ouvrables, et le travail ne commence qu’après accord écrit du client.

## 5. Exigences non négociables

- NN-1: La disponibilité mensuelle est d'au moins 99 %.
- NN-2: Les données personnelles sont hébergées uniquement sur des serveurs situés en Tunisie.
- NN-3: Les pages destinées aux clients respectent le WCAG 2.2 niveau AA.
- NN-4: La base de données est sauvegardée chaque jour et les sauvegardes sont conservées 14 jours.

## 6. Jalons et paiements

- M1, à livrer à la fin de la semaine 2 : prototype cliquable et modèle de données. Paiement : 30 % du prix.
- M2, à livrer à la fin de la semaine 3 : parcours utilisateur principal fonctionnel en préproduction. Paiement : 30 % du prix.
- M3, à livrer à la fin de la semaine 12 : back-office, notifications et rapport de tests. Paiement : 20 % du prix.
- M4, à livrer à la fin de la semaine 20 : mise en production et documentation de passation. Paiement : 20 % du prix.

## 7. Validation et réception

Le client dispose de 7 jours ouvrables pour valider chaque jalon. Un jalon est accepté lorsqu'il ne reste aucun défaut bloquant. Chaque jalon comprend jusqu'à 3 cycles de corrections ; les cycles supplémentaires sont des demandes de modification.

## 8. Conditions commerciales

Prix forfaitaire : 40 500 TND hors TVA, payé par jalon. Les factures sont payables sous 30 jours.

La propriété intellectuelle de l'application livrée est transférée au client après le paiement final. Garantie : le prestataire corrige sans frais les défauts signalés dans les 90 jours suivant la réception finale. Résiliation : chaque partie peut résilier avec un préavis écrit de 30 jours.

Les parties gardent les informations confidentielles pendant 1 ans après la fin du projet.

Retard : une pénalité de 0,5 % du prix par semaine de retard s'applique, plafonnée à 10 %.

## 9. Communication

Un point d'avancement de 60 minutes a lieu chaque mercredi. Les décisions qui modifient le périmètre, le prix ou les délais sont confirmées par écrit.

