# Note de cadrage - Médiathèque Ennour

Document d'entraînement synthétique RAFT2-P057. Le client, les personnes et les chiffres sont fictifs.

## 1. Contexte

Médiathèque Ennour souhaite une application de gestion des prêts de livres. L'objectif est de ne plus gérer les prêts à la main et de réduire les erreurs.

## 2. Parties

Le client est Médiathèque Ennour. L'adresse de contact projet du client est pm.raft2p057@example.com ; les urgences peuvent être signalées au +216 43 537 691. Le prestataire conçoit, développe, teste et déploie l'application.

## 3. Périmètre fonctionnel

### Dans le périmètre

- Réserver un livre déjà emprunté.
- Permettre aux bibliothécaires d'enregistrer les retours avec un lecteur de code-barres.
- Envoyer des rappels de retard par e-mail.
- Afficher les statistiques mensuelles de prêts.
- Les utilisateurs peuvent rechercher dans le catalogue par titre, auteur ou sujet.

### Non inclus

- Le paiement en ligne par carte ; les clients paient sur place.
- La tarification multi-devises.
- La migration des données historiques.

## 4. Évolutions du périmètre

Toute fonctionnalité non listée dans le périmètre est une demande de modification. Le prestataire envoie une estimation sous 5 jours ouvrables, et le travail ne commence qu’après accord écrit du client.

## 5. Exigences obligatoires

- NN-1: Les pages destinées aux clients respectent le WCAG 2.1 niveau AA.
- NN-2: La base de données est sauvegardée chaque jour et les sauvegardes sont conservées 14 jours.
- NN-3: La disponibilité mensuelle est d'au moins 99,9 %.
- NN-4: Au maximum 30 prêts par carte de membre.

## 6. Plan de livraison

- M1, à livrer à la fin de la semaine 2 : prototype cliquable et modèle de données. Paiement : 30 % du prix.
- M2, à livrer à la fin de la semaine 8 : parcours utilisateur principal fonctionnel en préproduction. Paiement : 30 % du prix.
- M3, à livrer à la fin de la semaine 12 : back-office, notifications et rapport de tests. Paiement : 20 % du prix.
- M4, à livrer à la fin de la semaine 18 : mise en production et documentation de passation. Paiement : 20 % du prix.

## 7. Validation et réception

Le client dispose de 10 jours ouvrables pour valider chaque jalon. Un jalon est accepté lorsqu'il ne reste aucun défaut bloquant. Chaque jalon comprend jusqu'à 1 cycles de corrections ; les cycles supplémentaires sont des demandes de modification.

## 8. Conditions commerciales

Prix forfaitaire : 7 000 TND hors TVA, payé par jalon. Les factures sont payables sous 15 jours.

La propriété intellectuelle de l'application livrée est transférée au client après le paiement final. Garantie : le prestataire corrige sans frais les défauts signalés dans les 60 jours suivant la réception finale. Résiliation : chaque partie peut résilier avec un préavis écrit de 30 jours.

Les parties gardent les informations confidentielles pendant 3 ans après la fin du projet.

## 9. Réunions

Un point d'avancement de 45 minutes a lieu chaque mercredi. Les décisions qui modifient le périmètre, le prix ou les délais sont confirmées par écrit.

