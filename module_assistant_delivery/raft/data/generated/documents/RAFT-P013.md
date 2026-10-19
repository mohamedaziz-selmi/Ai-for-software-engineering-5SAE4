# Cahier des charges : CoWork Lac

Document d'entraînement synthétique RAFT-P013. Le client, les personnes et les chiffres sont fictifs.

## 1. Contexte et objectifs

CoWork Lac souhaite une application de réservation de bureaux et salles de réunion. L'objectif est de remplacer la gestion manuelle des réservations et de réduire les erreurs.

## 2. Parties

Le client est CoWork Lac. L'adresse de contact projet du client est pm.raftp013@example.com, et le numéro pour les urgences est +216 21 167 926. Le prestataire conçoit, développe, teste et déploie l'application.

## 3. Périmètre

### 3.1 Inclus

- Les utilisateurs peuvent permettre aux gestionnaires de définir des règles par formule.
- Les utilisateurs peuvent réserver un bureau ou une salle de réunion.
- Les utilisateurs peuvent s'enregistrer avec un code QR au bureau.
- Les utilisateurs peuvent recevoir un récapitulatif mensuel d'utilisation par e-mail.
- Les utilisateurs peuvent bloquer des salles pour maintenance.

### 3.2 Exclus

- Le paiement en ligne par carte ; les clients paient sur place.
- La livraison à domicile.
- Les applications mobiles natives.

### 3.3 Demandes de modification

Toute fonctionnalité non listée dans la section 3.1 est une demande de modification. Le prestataire envoie une estimation sous 5 jours ouvrables, et le travail ne commence qu'après accord écrit du client.

## 4. Exigences non négociables

- NN-1: La disponibilité mensuelle est d'au moins 99,5 %.
- NN-2: Les mots de passe sont hachés avec Argon2id.
- NN-3: Au maximum 25 réservations par créneau d'une heure.
- NN-4: Les données personnelles sont hébergées uniquement sur des serveurs situés en Tunisie.

## 5. Jalons et paiements

- M1, à livrer à la fin de la semaine 2 : prototype cliquable et modèle de données. Paiement : 30 % du prix.
- M2, à livrer à la fin de la semaine 6 : parcours utilisateur principal fonctionnel en préproduction. Paiement : 30 % du prix.
- M3, à livrer à la fin de la semaine 8 : back-office, notifications et rapport de tests. Paiement : 20 % du prix.
- M4, à livrer à la fin de la semaine 16 : mise en production et documentation de passation. Paiement : 20 % du prix.

## 6. Recette

Le client dispose de 7 jours ouvrables pour valider chaque jalon. Un jalon est accepté lorsqu'il ne reste aucun défaut bloquant. Chaque jalon comprend jusqu'à 1 cycles de corrections ; les cycles supplémentaires sont des demandes de modification.

## 7. Conditions contractuelles

- Prix forfaitaire : 12 500 TND hors TVA, payé par jalon selon la section 5. Les factures sont payables sous 30 jours.
- La propriété intellectuelle de l'application livrée est transférée au client après le paiement final.
- Garantie: le prestataire corrige sans frais les défauts signalés dans les 60 jours suivant la réception finale.
- Résiliation: chaque partie peut résilier avec un préavis écrit de 30 jours.
- Confidentialité : les parties gardent les informations confidentielles pendant 2 ans après la fin du projet.

## 8. Communication

Un point d'avancement de 45 minutes a lieu chaque lundi. Les décisions qui modifient le périmètre, le prix ou les délais sont confirmées par écrit.

