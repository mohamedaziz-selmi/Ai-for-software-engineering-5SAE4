# Contrat de prestation : un portail de réservation de location de voitures pour Rent&Go Sfax

Document d'entraînement synthétique RAFT2-P011. Le client, les personnes et les chiffres sont fictifs.

## Article 1 - Contexte et objectifs

Aujourd'hui, Rent&Go Sfax gère ses réservations avec des tableurs et des appels téléphoniques. Ce projet livre un portail de réservation de location de voitures.

## Article 2 - Intervenants

Le client est Rent&Go Sfax. Les questions sur le projet sont à adresser à pm.raft2p011@example.com ; les urgences peuvent être signalées au +216 37 576 272. Le prestataire conçoit, développe, teste et déploie l'application.

## Article 3 - Périmètre des travaux

Le projet couvre les fonctionnalités suivantes : réserver une voiture et choisir l'agence de retrait; envoyer un e-mail de confirmation avec le numéro de réservation; permettre aux agents de confirmer ou refuser les réservations; téléverser une copie du permis de conduire; afficher au personnel un calendrier de disponibilité de la flotte.

Ne font pas partie du projet : les applications mobiles natives; le paiement en ligne par carte ; la tarification multi-devises.

## Article 4 - Demandes supplémentaires

Toute fonctionnalité non listée dans le périmètre est une demande de modification. Le prestataire envoie une estimation sous 3 jours ouvrables, et le travail ne commence qu’après accord écrit du client.

## Article 5 - Exigences non négociables

1. Les pages destinées aux clients respectent le WCAG 2.1 niveau AA.
2. La page d'accueil atteint un Largest Contentful Paint inférieur à 3 secondes sur une connexion 4G simulée.
3. La disponibilité mensuelle est d'au moins 99 %.
4. Les mots de passe sont hachés avec Argon2id.

## Article 6 - Planning et paiements

Le jalon M1 est dû à la fin de la semaine 4 et couvre : prototype cliquable et modèle de données ; il déclenche le paiement de 20 % du prix.
Le jalon M2 est dû à la fin de la semaine 5 et couvre : parcours utilisateur principal fonctionnel en préproduction ; il déclenche le paiement de 30 % du prix.
Le jalon M3 est dû à la fin de la semaine 8 et couvre : back-office, notifications et rapport de tests ; il déclenche le paiement de 30 % du prix.
Le jalon M4 est dû à la fin de la semaine 15 et couvre : mise en production et documentation de passation ; il déclenche le paiement de 20 % du prix.

## Article 7 - Validation et réception

Le client dispose de 10 jours ouvrables pour valider chaque jalon. Un jalon est accepté lorsqu'il ne reste aucun défaut bloquant. Chaque jalon comprend jusqu'à 1 cycles de corrections ; les cycles supplémentaires sont des demandes de modification.

## Article 8 - Conditions juridiques et financières

Prix forfaitaire : 16 000 TND hors TVA, payé par jalon. Les factures sont payables sous 45 jours.

La propriété intellectuelle de l'application livrée est transférée au client après le paiement final. Garantie : le prestataire corrige sans frais les défauts signalés dans les 90 jours suivant la réception finale. Résiliation : chaque partie peut résilier avec un préavis écrit de 30 jours.

Les parties gardent les informations confidentielles pendant 3 ans après la fin du projet.

Retard : une pénalité de 1 % du prix par semaine de retard s'applique, plafonnée à 10 %.

## Article 9 - Communication

Un point d'avancement de 60 minutes a lieu chaque lundi. Les décisions qui modifient le périmètre, le prix ou les délais sont confirmées par écrit.

