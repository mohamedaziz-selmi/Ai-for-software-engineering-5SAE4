# Cahier des charges : Café Jasmin

Document d'entraînement synthétique RAFT-P021. Le client, les personnes et les chiffres sont fictifs.

## 1. Contexte et objectifs

Café Jasmin souhaite un site de réservation de tables. L'objectif est de remplacer la gestion manuelle des réservations de table et de réduire les erreurs.

## 2. Parties

Le client est Café Jasmin. L'adresse de contact projet du client est pm.raftp021@example.com, et le numéro pour les urgences est +216 41 215 574. Le prestataire conçoit, développe, teste et déploie l'application.

## 3. Périmètre

### 3.1 Inclus

- Les utilisateurs peuvent permettre au personnel de voir les réservations du soir par table.
- Les utilisateurs peuvent choisir une date, une heure et un nombre de couverts.
- Les utilisateurs peuvent annuler une réservation depuis le lien de confirmation.
- Les utilisateurs peuvent gérer les horaires d'ouverture et les jours de fermeture.
- Les utilisateurs peuvent exporter les réservations du jour en CSV.

### 3.2 Exclus

- Les applications mobiles natives.
- La tarification multi-devises.
- Un programme de fidélité.

### 3.3 Demandes de modification

Toute fonctionnalité non listée dans la section 3.1 est une demande de modification. Le prestataire envoie une estimation sous 2 jours ouvrables, et le travail ne commence qu'après accord écrit du client.

## 4. Exigences non négociables

- NN-1: La page d'accueil atteint un Largest Contentful Paint inférieur à 2,5 secondes sur une connexion 4G simulée.
- NN-2: Les pages destinées aux clients respectent le WCAG 2.1 niveau AA.
- NN-3: La disponibilité mensuelle est d'au moins 99,9 %.
- NN-4: Les mots de passe sont hachés avec scrypt.

## 5. Jalons et paiements

- M1, à livrer à la fin de la semaine 7 : prototype cliquable et modèle de données. Paiement : 10 % du prix.
- M2, à livrer à la fin de la semaine 8 : parcours utilisateur principal fonctionnel en préproduction. Paiement : 40 % du prix.
- M3, à livrer à la fin de la semaine 13 : back-office, notifications et rapport de tests. Paiement : 30 % du prix.
- M4, à livrer à la fin de la semaine 17 : mise en production et documentation de passation. Paiement : 20 % du prix.

## 6. Recette

Le client dispose de 5 jours ouvrables pour valider chaque jalon. Un jalon est accepté lorsqu'il ne reste aucun défaut bloquant. Chaque jalon comprend jusqu'à 2 cycles de corrections ; les cycles supplémentaires sont des demandes de modification.

## 7. Conditions contractuelles

- Prix forfaitaire : 26 500 TND hors TVA, payé par jalon selon la section 5. Les factures sont payables sous 15 jours.
- La propriété intellectuelle de l'application livrée est transférée au client après le paiement final.
- Garantie: le prestataire corrige sans frais les défauts signalés dans les 90 jours suivant la réception finale.
- Résiliation: chaque partie peut résilier avec un préavis écrit de 15 jours.
- Confidentialité : les parties gardent les informations confidentielles pendant 1 ans après la fin du projet.
- Retard: une pénalité de 0,5 % du prix par semaine de retard s'applique, plafonnée à 10 %.

## 8. Communication

Un point d'avancement de 60 minutes a lieu chaque jeudi. Les décisions qui modifient le périmètre, le prix ou les délais sont confirmées par écrit.

