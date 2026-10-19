# Note de cadrage - Studio Atlas Fitness

Document d'entraînement synthétique RAFT2-P019. Le client, les personnes et les chiffres sont fictifs.

## Article 1 - Contexte et objectifs

Studio Atlas Fitness souhaite une application web de réservation de cours. L'objectif est de ne plus gérer les réservations à la main et de réduire les erreurs.

## Article 2 - Parties

Le client est Studio Atlas Fitness. L'adresse de contact projet du client est pm.raft2p019@example.com ; les urgences peuvent être signalées au +216 76 264 281. Le prestataire conçoit, développe, teste et déploie l'application.

## Article 3 - Périmètre des travaux

Fonctionnalités prévues : s'inscrire sur liste d'attente quand un cours est complet; permettre aux coachs de consulter la liste des participants; permettre au personnel de créer et modifier les cours; réserver et annuler un cours; recevoir un e-mail de rappel 24 heures avant un cours.

Sont expressément exclus de ce projet : la tarification multi-devises; le paiement en ligne par carte ; la migration des données historiques.

## Article 4 - Demandes de modification

Toute fonctionnalité non listée dans le périmètre est une demande de modification. Le prestataire envoie une estimation sous 3 jours ouvrables, et le travail ne commence qu’après accord écrit du client.

## Article 5 - Exigences obligatoires

1. Les pages destinées aux clients respectent le WCAG 2.2 niveau AA.
2. Au maximum 15 réservations par séance.
3. Les mots de passe sont hachés avec bcrypt.
4. La base de données est sauvegardée chaque jour et les sauvegardes sont conservées 30 jours.

## Article 6 - Planning et paiements

Le jalon M1 est dû à la fin de la semaine 2 et couvre : prototype cliquable et modèle de données ; il déclenche le paiement de 20 % du prix.
Le jalon M2 est dû à la fin de la semaine 6 et couvre : parcours utilisateur principal fonctionnel en préproduction ; il déclenche le paiement de 30 % du prix.
Le jalon M3 est dû à la fin de la semaine 13 et couvre : back-office, notifications et rapport de tests ; il déclenche le paiement de 30 % du prix.
Le jalon M4 est dû à la fin de la semaine 17 et couvre : mise en production et documentation de passation ; il déclenche le paiement de 20 % du prix.

## Article 7 - Validation des jalons

Le client dispose de 5 jours ouvrables pour valider chaque jalon. Un jalon est accepté lorsqu'il ne reste aucun défaut bloquant. Chaque jalon comprend jusqu'à 2 cycles de corrections ; les cycles supplémentaires sont des demandes de modification.

## Article 8 - Conditions juridiques et financières

Prix forfaitaire : 7 500 TND hors TVA, payé par jalon. Les factures sont payables sous 15 jours.

La propriété intellectuelle de l'application livrée est transférée au client après le paiement final. Garantie : le prestataire corrige sans frais les défauts signalés dans les 90 jours suivant la réception finale. Résiliation : chaque partie peut résilier avec un préavis écrit de 15 jours.

Les parties gardent les informations confidentielles pendant 2 ans après la fin du projet.

Retard : une pénalité de 2 % du prix par semaine de retard s'applique, plafonnée à 10 %.

## Article 9 - Réunions

Un point d'avancement de 60 minutes a lieu chaque jeudi. Les décisions qui modifient le périmètre, le prix ou les délais sont confirmées par écrit.

