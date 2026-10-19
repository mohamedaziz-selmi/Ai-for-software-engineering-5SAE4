# Cahier des charges : Café Jasmin

Document d'entraînement synthétique RAFT-P001. Le client, les personnes et les chiffres sont fictifs.

## 1. Contexte et objectifs

Café Jasmin souhaite un site de réservation de tables. L'objectif est de remplacer la gestion manuelle des réservations de table et de réduire les erreurs.

## 2. Parties

Le client est Café Jasmin. L'adresse de contact projet du client est pm.raftp001@example.com, et le numéro pour les urgences est +216 83 796 644. Le prestataire conçoit, développe, teste et déploie l'application.

## 3. Périmètre

### 3.1 Inclus

- Les utilisateurs peuvent choisir une date, une heure et un nombre de couverts.
- Les utilisateurs peuvent annuler une réservation depuis le lien de confirmation.
- Les utilisateurs peuvent recevoir une confirmation par SMS.
- Les utilisateurs peuvent gérer les horaires d'ouverture et les jours de fermeture.
- Les utilisateurs peuvent exporter les réservations du jour en CSV.

### 3.2 Exclus

- Un programme de fidélité.
- Les applications mobiles natives.
- La tarification multi-devises.

### 3.3 Demandes de modification

Toute fonctionnalité non listée dans la section 3.1 est une demande de modification. Le prestataire envoie une estimation sous 3 jours ouvrables, et le travail ne commence qu'après accord écrit du client.

## 4. Exigences non négociables

- NN-1: Les données personnelles sont hébergées uniquement sur des serveurs situés en Tunisie ou dans l'Union européenne.
- NN-2: Les mots de passe sont hachés avec bcrypt.
- NN-3: Au maximum 20 réservations de table par service de 30 minutes.
- NN-4: Chaque compte administrateur utilise l'authentification à deux facteurs.

## 5. Jalons et paiements

- M1, à livrer à la fin de la semaine 6 : prototype cliquable et modèle de données. Paiement : 10 % du prix.
- M2, à livrer à la fin de la semaine 9 : parcours utilisateur principal fonctionnel en préproduction. Paiement : 40 % du prix.
- M3, à livrer à la fin de la semaine 10 : back-office, notifications et rapport de tests. Paiement : 30 % du prix.
- M4, à livrer à la fin de la semaine 17 : mise en production et documentation de passation. Paiement : 20 % du prix.

## 6. Recette

Le client dispose de 7 jours ouvrables pour valider chaque jalon. Un jalon est accepté lorsqu'il ne reste aucun défaut bloquant. Chaque jalon comprend jusqu'à 3 cycles de corrections ; les cycles supplémentaires sont des demandes de modification.

## 7. Conditions contractuelles

- Prix forfaitaire : 19 000 TND hors TVA, payé par jalon selon la section 5. Les factures sont payables sous 15 jours.
- La propriété intellectuelle de l'application livrée est transférée au client après le paiement final.
- Garantie: le prestataire corrige sans frais les défauts signalés dans les 30 jours suivant la réception finale.
- Résiliation: chaque partie peut résilier avec un préavis écrit de 30 jours.
- Confidentialité : les parties gardent les informations confidentielles pendant 1 ans après la fin du projet.

## 8. Communication

Un point d'avancement de 30 minutes a lieu chaque mercredi. Les décisions qui modifient le périmètre, le prix ou les délais sont confirmées par écrit.

