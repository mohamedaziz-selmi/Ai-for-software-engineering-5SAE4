# Cahier des charges : Logistika Express

Document d'entraînement synthétique RAFT-P029. Le client, les personnes et les chiffres sont fictifs.

## 1. Contexte et objectifs

Logistika Express souhaite un tableau de bord de suivi de colis. L'objectif est de remplacer la gestion manuelle des colis et de réduire les erreurs.

## 2. Parties

Le client est Logistika Express. L'adresse de contact projet du client est pm.raftp029@example.com, et le numéro pour les urgences est +216 56 380 379. Le prestataire conçoit, développe, teste et déploie l'application.

## 3. Périmètre

### 3.1 Inclus

- Les utilisateurs peuvent suivre un colis avec son numéro de suivi.
- Les utilisateurs peuvent affecter les colis aux tournées de livraison.
- Les utilisateurs peuvent informer les clients par e-mail quand un colis est en cours de livraison.
- Les utilisateurs peuvent afficher un rapport quotidien de performance des livraisons.
- Les utilisateurs peuvent permettre aux livreurs de mettre à jour le statut depuis le navigateur du téléphone.

### 3.2 Exclus

- La tarification multi-devises.
- Les applications mobiles natives.
- Le paiement en ligne par carte ; les clients paient sur place.

### 3.3 Demandes de modification

Toute fonctionnalité non listée dans la section 3.1 est une demande de modification. Le prestataire envoie une estimation sous 5 jours ouvrables, et le travail ne commence qu'après accord écrit du client.

## 4. Exigences non négociables

- NN-1: Les données personnelles sont hébergées uniquement sur des serveurs situés en Tunisie.
- NN-2: La disponibilité mensuelle est d'au moins 99,5 %.
- NN-3: Aucune donnée personnelle n'apparaît dans les journaux de l'application.
- NN-4: La base de données est sauvegardée chaque jour et les sauvegardes sont conservées 14 jours.

## 5. Jalons et paiements

- M1, à livrer à la fin de la semaine 4 : prototype cliquable et modèle de données. Paiement : 25 % du prix.
- M2, à livrer à la fin de la semaine 5 : parcours utilisateur principal fonctionnel en préproduction. Paiement : 25 % du prix.
- M3, à livrer à la fin de la semaine 12 : back-office, notifications et rapport de tests. Paiement : 25 % du prix.
- M4, à livrer à la fin de la semaine 20 : mise en production et documentation de passation. Paiement : 25 % du prix.

## 6. Recette

Le client dispose de 5 jours ouvrables pour valider chaque jalon. Un jalon est accepté lorsqu'il ne reste aucun défaut bloquant. Chaque jalon comprend jusqu'à 3 cycles de corrections ; les cycles supplémentaires sont des demandes de modification.

## 7. Conditions contractuelles

- Prix forfaitaire : 26 500 TND hors TVA, payé par jalon selon la section 5. Les factures sont payables sous 15 jours.
- La propriété intellectuelle de l'application livrée est transférée au client après le paiement final.
- Garantie: le prestataire corrige sans frais les défauts signalés dans les 90 jours suivant la réception finale.
- Résiliation: chaque partie peut résilier avec un préavis écrit de 15 jours.
- Confidentialité : les parties gardent les informations confidentielles pendant 1 ans après la fin du projet.
- Retard: une pénalité de 2 % du prix par semaine de retard s'applique, plafonnée à 10 %.

## 8. Communication

Un point d'avancement de 30 minutes a lieu chaque jeudi. Les décisions qui modifient le périmètre, le prix ou les délais sont confirmées par écrit.

