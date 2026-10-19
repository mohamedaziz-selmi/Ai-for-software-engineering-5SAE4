# Cahier des charges : Médiathèque Ennour

Document d'entraînement synthétique RAFT-P023. Le client, les personnes et les chiffres sont fictifs.

## 1. Contexte et objectifs

Médiathèque Ennour souhaite une application de gestion des prêts de livres. L'objectif est de remplacer la gestion manuelle des prêts et de réduire les erreurs.

## 2. Parties

Le client est Médiathèque Ennour. L'adresse de contact projet du client est pm.raftp023@example.com, et le numéro pour les urgences est +216 73 259 421. Le prestataire conçoit, développe, teste et déploie l'application.

## 3. Périmètre

### 3.1 Inclus

- Les utilisateurs peuvent prolonger un prêt en ligne une fois.
- Les utilisateurs peuvent envoyer des rappels de retard par e-mail.
- Les utilisateurs peuvent rechercher dans le catalogue par titre, auteur ou sujet.
- Les utilisateurs peuvent afficher les statistiques mensuelles de prêts.
- Les utilisateurs peuvent permettre aux bibliothécaires d'enregistrer les retours avec un lecteur de code-barres.

### 3.2 Exclus

- La livraison à domicile.
- La migration des données historiques.
- Un programme de fidélité.

### 3.3 Demandes de modification

Toute fonctionnalité non listée dans la section 3.1 est une demande de modification. Le prestataire envoie une estimation sous 2 jours ouvrables, et le travail ne commence qu'après accord écrit du client.

## 4. Exigences non négociables

- NN-1: La page d'accueil atteint un Largest Contentful Paint inférieur à 2 secondes sur une connexion 4G simulée.
- NN-2: Au maximum 15 prêts par carte de membre.
- NN-3: La disponibilité mensuelle est d'au moins 99,9 %.
- NN-4: Les pages destinées aux clients respectent le WCAG 2.1 niveau AA.

## 5. Jalons et paiements

- M1, à livrer à la fin de la semaine 2 : prototype cliquable et modèle de données. Paiement : 30 % du prix.
- M2, à livrer à la fin de la semaine 8 : parcours utilisateur principal fonctionnel en préproduction. Paiement : 30 % du prix.
- M3, à livrer à la fin de la semaine 13 : back-office, notifications et rapport de tests. Paiement : 20 % du prix.
- M4, à livrer à la fin de la semaine 16 : mise en production et documentation de passation. Paiement : 20 % du prix.

## 6. Recette

Le client dispose de 7 jours ouvrables pour valider chaque jalon. Un jalon est accepté lorsqu'il ne reste aucun défaut bloquant. Chaque jalon comprend jusqu'à 3 cycles de corrections ; les cycles supplémentaires sont des demandes de modification.

## 7. Conditions contractuelles

- Prix forfaitaire : 24 000 TND hors TVA, payé par jalon selon la section 5. Les factures sont payables sous 15 jours.
- La propriété intellectuelle de l'application livrée est transférée au client après le paiement final.
- Garantie: le prestataire corrige sans frais les défauts signalés dans les 30 jours suivant la réception finale.
- Résiliation: chaque partie peut résilier avec un préavis écrit de 30 jours.
- Confidentialité : les parties gardent les informations confidentielles pendant 2 ans après la fin du projet.

## 8. Communication

Un point d'avancement de 60 minutes a lieu chaque mercredi. Les décisions qui modifient le périmètre, le prix ou les délais sont confirmées par écrit.

