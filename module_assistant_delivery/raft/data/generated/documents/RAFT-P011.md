# Cahier des charges : Studio Atlas Fitness

Document d'entraînement synthétique RAFT-P011. Le client, les personnes et les chiffres sont fictifs.

## 1. Contexte et objectifs

Studio Atlas Fitness souhaite une application web de réservation de cours. L'objectif est de remplacer la gestion manuelle des réservations et de réduire les erreurs.

## 2. Parties

Le client est Studio Atlas Fitness. L'adresse de contact projet du client est pm.raftp011@example.com, et le numéro pour les urgences est +216 53 278 659. Le prestataire conçoit, développe, teste et déploie l'application.

## 3. Périmètre

### 3.1 Inclus

- Les utilisateurs peuvent permettre au personnel de créer et modifier les cours.
- Les utilisateurs peuvent réserver et annuler un cours.
- Les utilisateurs peuvent recevoir un e-mail de rappel 24 heures avant un cours.
- Les utilisateurs peuvent s'inscrire sur liste d'attente quand un cours est complet.
- Les utilisateurs peuvent consulter le planning hebdomadaire des cours.

### 3.2 Exclus

- La migration des données historiques.
- Le paiement en ligne par carte ; les clients paient sur place.
- Les applications mobiles natives.

### 3.3 Demandes de modification

Toute fonctionnalité non listée dans la section 3.1 est une demande de modification. Le prestataire envoie une estimation sous 2 jours ouvrables, et le travail ne commence qu'après accord écrit du client.

## 4. Exigences non négociables

- NN-1: La disponibilité mensuelle est d'au moins 99,5 %.
- NN-2: Les pages destinées aux clients respectent le WCAG 2.2 niveau AA.
- NN-3: La base de données est sauvegardée chaque jour et les sauvegardes sont conservées 14 jours.
- NN-4: La page d'accueil atteint un Largest Contentful Paint inférieur à 2 secondes sur une connexion 4G simulée.

## 5. Jalons et paiements

- M1, à livrer à la fin de la semaine 4 : prototype cliquable et modèle de données. Paiement : 10 % du prix.
- M2, à livrer à la fin de la semaine 6 : parcours utilisateur principal fonctionnel en préproduction. Paiement : 40 % du prix.
- M3, à livrer à la fin de la semaine 13 : back-office, notifications et rapport de tests. Paiement : 30 % du prix.
- M4, à livrer à la fin de la semaine 20 : mise en production et documentation de passation. Paiement : 20 % du prix.

## 6. Recette

Le client dispose de 10 jours ouvrables pour valider chaque jalon. Un jalon est accepté lorsqu'il ne reste aucun défaut bloquant. Chaque jalon comprend jusqu'à 1 cycles de corrections ; les cycles supplémentaires sont des demandes de modification.

## 7. Conditions contractuelles

- Prix forfaitaire : 41 500 TND hors TVA, payé par jalon selon la section 5. Les factures sont payables sous 45 jours.
- La propriété intellectuelle de l'application livrée est transférée au client après le paiement final.
- Garantie: le prestataire corrige sans frais les défauts signalés dans les 30 jours suivant la réception finale.
- Résiliation: chaque partie peut résilier avec un préavis écrit de 15 jours.
- Confidentialité : les parties gardent les informations confidentielles pendant 3 ans après la fin du projet.

## 8. Communication

Un point d'avancement de 30 minutes a lieu chaque jeudi. Les décisions qui modifient le périmètre, le prix ou les délais sont confirmées par écrit.

