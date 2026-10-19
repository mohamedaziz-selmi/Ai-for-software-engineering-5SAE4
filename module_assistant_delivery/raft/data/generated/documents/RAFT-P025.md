# Cahier des charges : CoWork Lac

Document d'entraînement synthétique RAFT-P025. Le client, les personnes et les chiffres sont fictifs.

## 1. Contexte et objectifs

CoWork Lac souhaite une application de réservation de bureaux et salles de réunion. L'objectif est de remplacer la gestion manuelle des réservations et de réduire les erreurs.

## 2. Parties

Le client est CoWork Lac. L'adresse de contact projet du client est pm.raftp025@example.com, et le numéro pour les urgences est +216 44 718 630. Le prestataire conçoit, développe, teste et déploie l'application.

## 3. Périmètre

### 3.1 Inclus

- Les utilisateurs peuvent voir un plan d'étage avec les bureaux libres.
- Les utilisateurs peuvent bloquer des salles pour maintenance.
- Les utilisateurs peuvent recevoir un récapitulatif mensuel d'utilisation par e-mail.
- Les utilisateurs peuvent permettre aux gestionnaires de définir des règles par formule.
- Les utilisateurs peuvent s'enregistrer avec un code QR au bureau.

### 3.2 Exclus

- La tarification multi-devises.
- Les applications mobiles natives.
- Un programme de fidélité.

### 3.3 Demandes de modification

Toute fonctionnalité non listée dans la section 3.1 est une demande de modification. Le prestataire envoie une estimation sous 2 jours ouvrables, et le travail ne commence qu'après accord écrit du client.

## 4. Exigences non négociables

- NN-1: La page d'accueil atteint un Largest Contentful Paint inférieur à 2,5 secondes sur une connexion 4G simulée.
- NN-2: Au maximum 15 réservations par créneau d'une heure.
- NN-3: Chaque compte administrateur utilise l'authentification à deux facteurs.
- NN-4: Aucune donnée personnelle n'apparaît dans les journaux de l'application.

## 5. Jalons et paiements

- M1, à livrer à la fin de la semaine 3 : prototype cliquable et modèle de données. Paiement : 25 % du prix.
- M2, à livrer à la fin de la semaine 10 : parcours utilisateur principal fonctionnel en préproduction. Paiement : 25 % du prix.
- M3, à livrer à la fin de la semaine 12 : back-office, notifications et rapport de tests. Paiement : 25 % du prix.
- M4, à livrer à la fin de la semaine 18 : mise en production et documentation de passation. Paiement : 25 % du prix.

## 6. Recette

Le client dispose de 3 jours ouvrables pour valider chaque jalon. Un jalon est accepté lorsqu'il ne reste aucun défaut bloquant. Chaque jalon comprend jusqu'à 1 cycles de corrections ; les cycles supplémentaires sont des demandes de modification.

## 7. Conditions contractuelles

- Prix forfaitaire : 41 000 TND hors TVA, payé par jalon selon la section 5. Les factures sont payables sous 15 jours.
- La propriété intellectuelle de l'application livrée est transférée au client après le paiement final.
- Garantie: le prestataire corrige sans frais les défauts signalés dans les 60 jours suivant la réception finale.
- Résiliation: chaque partie peut résilier avec un préavis écrit de 15 jours.
- Confidentialité : les parties gardent les informations confidentielles pendant 3 ans après la fin du projet.

## 8. Communication

Un point d'avancement de 60 minutes a lieu chaque jeudi. Les décisions qui modifient le périmètre, le prix ou les délais sont confirmées par écrit.

