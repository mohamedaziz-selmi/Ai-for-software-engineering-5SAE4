# Cahier des charges : Logistika Express

Document d'entraînement synthétique RAFT2-P021. Le client, les personnes et les chiffres sont fictifs.

## 1. Présentation du projet

Logistika Express souhaite un tableau de bord de suivi de colis. L'objectif est de ne plus gérer les colis à la main et de réduire les erreurs.

## 2. Parties

Le client est Logistika Express. L'adresse de contact projet du client est pm.raft2p021@example.com ; les urgences peuvent être signalées au +216 31 234 664. Le prestataire conçoit, développe, teste et déploie l'application.

## 3. Périmètre fonctionnel

| Fonctionnalité | Statut |
|---|---|
| Un programme de fidélité | Exclu |
| Le paiement en ligne par carte  | Exclu |
| Afficher un rapport quotidien de performance des livraisons | Inclus |
| Permettre aux livreurs de mettre à jour le statut depuis le navigateur du téléphone | Inclus |
| Affecter les colis aux tournées de livraison | Inclus |
| Importer des colis depuis un fichier CSV | Inclus |
| La livraison à domicile | Exclu |
| Informer les clients par e-mail quand un colis est en cours de livraison | Inclus |

## 4. Demandes supplémentaires

Toute fonctionnalité non listée dans le périmètre est une demande de modification. Le prestataire envoie une estimation sous 2 jours ouvrables, et le travail ne commence qu’après accord écrit du client.

## 5. Exigences essentielles

- NN-1: Les mots de passe sont hachés avec bcrypt.
- NN-2: La disponibilité mensuelle est d'au moins 99,5 %.
- NN-3: Les pages destinées aux clients respectent le WCAG 2.1 niveau AA.
- NN-4: Les données personnelles sont hébergées uniquement sur des serveurs situés dans l'Union européenne.

## 6. Planning et paiements

| Jalon | Échéance | Livrables | Paiement |
|---|---|---|---|
| M1 | Fin de la semaine 2 | Prototype cliquable et modèle de données | 30% |
| M2 | Fin de la semaine 12 | Parcours utilisateur principal fonctionnel en préproduction | 30% |
| M3 | Fin de la semaine 13 | Back-office, notifications et rapport de tests | 20% |
| M4 | Fin de la semaine 18 | Mise en production et documentation de passation | 20% |

## 7. Validation et réception

Le client dispose de 7 jours ouvrables pour valider chaque jalon. Un jalon est accepté lorsqu'il ne reste aucun défaut bloquant. Chaque jalon comprend jusqu'à 1 cycles de corrections ; les cycles supplémentaires sont des demandes de modification.

## 8. Conditions contractuelles

| Clause | Valeur |
|---|---|
| Prix | Prix forfaitaire : 25 000 TND hors TVA |
| Factures | Les factures sont payables sous 30 jours |
| Garantie | Le prestataire corrige sans frais les défauts signalés dans les 60 jours suivant la réception finale |
| Résiliation | Chaque partie peut résilier avec un préavis écrit de 30 jours |
| Propriété intellectuelle | La propriété intellectuelle de l'application livrée est transférée au client après le paiement final |
Les parties gardent les informations confidentielles pendant 2 ans après la fin du projet.

Retard : une pénalité de 1 % du prix par semaine de retard s'applique, plafonnée à 10 %.

## 9. Réunions

Un point d'avancement de 60 minutes a lieu chaque lundi. Les décisions qui modifient le périmètre, le prix ou les délais sont confirmées par écrit.

