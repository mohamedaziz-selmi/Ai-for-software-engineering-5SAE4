# Cahier des charges : Médiathèque Ennour

Document d'entraînement synthétique RAFT-P033. Le client, les personnes et les chiffres sont fictifs.

## 1. Contexte et objectifs

Médiathèque Ennour souhaite une application de gestion des prêts de livres. L'objectif est de remplacer la gestion manuelle des prêts et de réduire les erreurs.

## 2. Parties

Le client est Médiathèque Ennour. L'adresse de contact projet du client est pm.raftp033@example.com, et le numéro pour les urgences est +216 42 906 954. Le prestataire conçoit, développe, teste et déploie l'application.

## 3. Périmètre

### 3.1 Inclus

- Les utilisateurs peuvent réserver un livre déjà emprunté.
- Les utilisateurs peuvent rechercher dans le catalogue par titre, auteur ou sujet.
- Les utilisateurs peuvent permettre aux bibliothécaires d'enregistrer les retours avec un lecteur de code-barres.
- Les utilisateurs peuvent prolonger un prêt en ligne une fois.
- Les utilisateurs peuvent afficher les statistiques mensuelles de prêts.

### 3.2 Exclus

- La livraison à domicile.
- La migration des données historiques.
- Les applications mobiles natives.

### 3.3 Demandes de modification

Toute fonctionnalité non listée dans la section 3.1 est une demande de modification. Le prestataire envoie une estimation sous 5 jours ouvrables, et le travail ne commence qu'après accord écrit du client.

## 4. Exigences non négociables

- NN-1: Les mots de passe sont hachés avec bcrypt.
- NN-2: La base de données est sauvegardée chaque jour et les sauvegardes sont conservées 14 jours.
- NN-3: Chaque compte administrateur utilise l'authentification à deux facteurs.
- NN-4: Les données personnelles sont hébergées uniquement sur des serveurs situés en Tunisie ou dans l'Union européenne.

## 5. Jalons et paiements

- M1, à livrer à la fin de la semaine 6 : prototype cliquable et modèle de données. Paiement : 30 % du prix.
- M2, à livrer à la fin de la semaine 8 : parcours utilisateur principal fonctionnel en préproduction. Paiement : 30 % du prix.
- M3, à livrer à la fin de la semaine 10 : back-office, notifications et rapport de tests. Paiement : 20 % du prix.
- M4, à livrer à la fin de la semaine 16 : mise en production et documentation de passation. Paiement : 20 % du prix.

## 6. Recette

Le client dispose de 5 jours ouvrables pour valider chaque jalon. Un jalon est accepté lorsqu'il ne reste aucun défaut bloquant. Chaque jalon comprend jusqu'à 2 cycles de corrections ; les cycles supplémentaires sont des demandes de modification.

## 7. Conditions contractuelles

- Prix forfaitaire : 26 500 TND hors TVA, payé par jalon selon la section 5. Les factures sont payables sous 30 jours.
- La propriété intellectuelle de l'application livrée est transférée au client après le paiement final.
- Garantie: le prestataire corrige sans frais les défauts signalés dans les 60 jours suivant la réception finale.
- Résiliation: chaque partie peut résilier avec un préavis écrit de 30 jours.
- Confidentialité : les parties gardent les informations confidentielles pendant 1 ans après la fin du projet.

## 8. Communication

Un point d'avancement de 45 minutes a lieu chaque lundi. Les décisions qui modifient le périmètre, le prix ou les délais sont confirmées par écrit.

