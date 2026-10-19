# Cahier des charges : Rent&Go Sfax

Document d'entraînement synthétique RAFT2-P049. Le client, les personnes et les chiffres sont fictifs.

## 1. Présentation du projet

Rent&Go Sfax souhaite un portail de réservation de location de voitures. L'objectif est de ne plus gérer les réservations à la main et de réduire les erreurs.

## 2. Intervenants

Le client est Rent&Go Sfax. L'adresse de contact projet du client est pm.raft2p049@example.com ; les urgences peuvent être signalées au +216 90 848 101. Le prestataire conçoit, développe, teste et déploie l'application.

## 3. Périmètre

### Inclus

- Afficher au personnel un calendrier de disponibilité de la flotte.
- Les utilisateurs peuvent réserver une voiture et choisir l'agence de retrait.
- Les utilisateurs peuvent téléverser une copie du permis de conduire.
- Les utilisateurs peuvent rechercher les voitures disponibles par date et catégorie.
- Envoyer un e-mail de confirmation avec le numéro de réservation.

### Hors périmètre

- Les applications mobiles natives.
- Un programme de fidélité.
- La migration des données historiques.

## 4. Évolutions du périmètre

Toute fonctionnalité non listée dans le périmètre est une demande de modification. Le prestataire envoie une estimation sous 3 jours ouvrables, et le travail ne commence qu’après accord écrit du client.

## 5. Exigences essentielles

- NN-1: Les pages destinées aux clients respectent le WCAG 2.2 niveau AA.
- NN-2: Au maximum 20 réservations par heure de retrait.
- NN-3: La base de données est sauvegardée chaque jour et les sauvegardes sont conservées 14 jours.
- NN-4: La page d'accueil atteint un Largest Contentful Paint inférieur à 2,5 secondes sur une connexion 4G simulée.

## 6. Plan de livraison

- M1, à livrer à la fin de la semaine 7 : prototype cliquable et modèle de données. Paiement : 25 % du prix.
- M2, à livrer à la fin de la semaine 11 : parcours utilisateur principal fonctionnel en préproduction. Paiement : 25 % du prix.
- M3, à livrer à la fin de la semaine 14 : back-office, notifications et rapport de tests. Paiement : 25 % du prix.
- M4, à livrer à la fin de la semaine 15 : mise en production et documentation de passation. Paiement : 25 % du prix.

## 7. Validation des jalons

Le client dispose de 10 jours ouvrables pour valider chaque jalon. Un jalon est accepté lorsqu'il ne reste aucun défaut bloquant. Chaque jalon comprend jusqu'à 1 cycles de corrections ; les cycles supplémentaires sont des demandes de modification.

## 8. Conditions juridiques et financières

Prix forfaitaire : 17 500 TND hors TVA, payé par jalon. Les factures sont payables sous 30 jours.

La propriété intellectuelle de l'application livrée est transférée au client après le paiement final. Garantie : le prestataire corrige sans frais les défauts signalés dans les 90 jours suivant la réception finale. Résiliation : chaque partie peut résilier avec un préavis écrit de 30 jours.

Les parties gardent les informations confidentielles pendant 2 ans après la fin du projet.

Retard : une pénalité de 0,5 % du prix par semaine de retard s'applique, plafonnée à 5 %.

## 9. Communication

Un point d'avancement de 60 minutes a lieu chaque jeudi. Les décisions qui modifient le périmètre, le prix ou les délais sont confirmées par écrit.

