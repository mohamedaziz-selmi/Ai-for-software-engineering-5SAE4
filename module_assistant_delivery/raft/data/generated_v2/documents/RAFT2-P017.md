# Cahier des charges : Rent&Go Sfax

Document d'entraînement synthétique RAFT2-P017. Le client, les personnes et les chiffres sont fictifs.

## 1. Contexte et objectifs

Rent&Go Sfax souhaite un portail de réservation de location de voitures. L'objectif est de ne plus gérer les réservations à la main et de réduire les erreurs.

## 2. Parties

Le client est Rent&Go Sfax. Les questions sur le projet sont à adresser à pm.raft2p017@example.com ; les urgences peuvent être signalées au +216 34 567 223. Le prestataire conçoit, développe, teste et déploie l'application.

## 3. Périmètre

### Inclus

- Permettre aux agents de confirmer ou refuser les réservations.
- Les utilisateurs peuvent rechercher les voitures disponibles par date et catégorie.
- Afficher au personnel un calendrier de disponibilité de la flotte.
- Téléverser une copie du permis de conduire.
- Envoyer un e-mail de confirmation avec le numéro de réservation.

### Exclus

- La tarification multi-devises.
- La migration des données historiques.
- Le paiement en ligne par carte ; les clients paient sur place.

## 4. Demandes supplémentaires

Les fonctionnalités non décrites ci-dessus sont traitées comme des demandes de modification. Le prestataire envoie une estimation sous 5 jours ouvrables, et le travail ne commence qu’après accord écrit du client.

## 5. Exigences obligatoires

- NN-1: La base de données est sauvegardée chaque jour et les sauvegardes sont conservées 30 jours.
- NN-2: La disponibilité mensuelle est d'au moins 99,5 %.
- NN-3: Les données personnelles sont hébergées uniquement sur des serveurs situés en Tunisie.
- NN-4: Les mots de passe sont hachés avec Argon2id.

## 6. Jalons et paiements

- M1, à livrer à la fin de la semaine 6 : prototype cliquable et modèle de données. Paiement : 30 % du prix.
- M2, à livrer à la fin de la semaine 7 : parcours utilisateur principal fonctionnel en préproduction. Paiement : 30 % du prix.
- M3, à livrer à la fin de la semaine 12 : back-office, notifications et rapport de tests. Paiement : 20 % du prix.
- M4, à livrer à la fin de la semaine 16 : mise en production et documentation de passation. Paiement : 20 % du prix.

## 7. Recette

Le client dispose de 3 jours ouvrables pour valider chaque jalon. Un jalon est accepté lorsqu'il ne reste aucun défaut bloquant. Chaque jalon comprend jusqu'à 2 cycles de corrections ; les cycles supplémentaires sont des demandes de modification.

## 8. Conditions juridiques et financières

Prix forfaitaire : 38 500 TND hors TVA, payé par jalon. Les factures sont payables sous 15 jours.

La propriété intellectuelle de l'application livrée est transférée au client après le paiement final. Garantie : le prestataire corrige sans frais les défauts signalés dans les 30 jours suivant la réception finale. Résiliation : chaque partie peut résilier avec un préavis écrit de 30 jours.

Les parties gardent les informations confidentielles pendant 1 ans après la fin du projet.

## 9. Communication

Un point d'avancement de 45 minutes a lieu chaque lundi. Les décisions qui modifient le périmètre, le prix ou les délais sont confirmées par écrit.

