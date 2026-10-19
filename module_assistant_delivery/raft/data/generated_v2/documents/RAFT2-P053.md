# Cahier des charges : Studio Atlas Fitness

Document d'entraînement synthétique RAFT2-P053. Le client, les personnes et les chiffres sont fictifs.

## 1. Contexte et objectifs

Aujourd'hui, Studio Atlas Fitness gère ses réservations avec des tableurs et des appels téléphoniques. Ce projet livre une application web de réservation de cours.

## 2. Intervenants

Le client est Studio Atlas Fitness. L'adresse de contact projet du client est pm.raft2p053@example.com ; les urgences peuvent être signalées au +216 24 387 981. Le prestataire conçoit, développe, teste et déploie l'application.

## 3. Périmètre des travaux

| Fonctionnalité | Statut |
|---|---|
| Réserver et annuler un cours | Inclus |
| Permettre au personnel de créer et modifier les cours | Inclus |
| La tarification multi-devises | Exclu |
| S'inscrire sur liste d'attente quand un cours est complet | Inclus |
| Recevoir un e-mail de rappel 24 heures avant un cours | Inclus |
| Permettre aux coachs de consulter la liste des participants | Inclus |
| Le paiement en ligne par carte  | Exclu |
| Un programme de fidélité | Exclu |

## 4. Demandes supplémentaires

Les fonctionnalités non décrites ci-dessus sont traitées comme des demandes de modification. Le prestataire envoie une estimation sous 3 jours ouvrables, et le travail ne commence qu’après accord écrit du client.

## 5. Exigences non négociables

- NN-1: La page d'accueil atteint un Largest Contentful Paint inférieur à 3 secondes sur une connexion 4G simulée.
- NN-2: Les pages destinées aux clients respectent le WCAG 2.2 niveau AA.
- NN-3: La disponibilité mensuelle est d'au moins 99,9 %.
- NN-4: Les mots de passe sont hachés avec scrypt.

## 6. Planning et paiements

| Jalon | Échéance | Livrables | Paiement |
|---|---|---|---|
| M1 | Fin de la semaine 4 | Prototype cliquable et modèle de données | 20% |
| M2 | Fin de la semaine 10 | Parcours utilisateur principal fonctionnel en préproduction | 30% |
| M3 | Fin de la semaine 13 | Back-office, notifications et rapport de tests | 30% |
| M4 | Fin de la semaine 15 | Mise en production et documentation de passation | 20% |

## 7. Recette

Le client dispose de 3 jours ouvrables pour valider chaque jalon. Un jalon est accepté lorsqu'il ne reste aucun défaut bloquant. Chaque jalon comprend jusqu'à 2 cycles de corrections ; les cycles supplémentaires sont des demandes de modification.

## 8. Conditions contractuelles

| Clause | Valeur |
|---|---|
| Prix | Prix forfaitaire : 21 500 TND hors TVA |
| Factures | Les factures sont payables sous 45 jours |
| Garantie | Le prestataire corrige sans frais les défauts signalés dans les 30 jours suivant la réception finale |
| Résiliation | Chaque partie peut résilier avec un préavis écrit de 15 jours |
| Propriété intellectuelle | La propriété intellectuelle de l'application livrée est transférée au client après le paiement final |
Les parties gardent les informations confidentielles pendant 2 ans après la fin du projet.

## 9. Gouvernance du projet

Un point d'avancement de 60 minutes a lieu chaque jeudi. Les décisions qui modifient le périmètre, le prix ou les délais sont confirmées par écrit.

