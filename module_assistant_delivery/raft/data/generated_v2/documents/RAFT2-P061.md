# Contrat de prestation : un tableau de bord de suivi de colis pour Logistika Express

Document d'entraînement synthétique RAFT2-P061. Le client, les personnes et les chiffres sont fictifs.

## 1. Contexte

Logistika Express souhaite un tableau de bord de suivi de colis. L'objectif est de ne plus gérer les colis à la main et de réduire les erreurs.

## 2. Parties

Le client est Logistika Express. Les questions sur le projet sont à adresser à pm.raft2p061@example.com ; les urgences peuvent être signalées au +216 22 848 758. Le prestataire conçoit, développe, teste et déploie l'application.

## 3. Périmètre des travaux

| Fonctionnalité | Statut |
|---|---|
| Suivre un colis avec son numéro de suivi | Inclus |
| Informer les clients par e-mail quand un colis est en cours de livraison | Inclus |
| Afficher un rapport quotidien de performance des livraisons | Inclus |
| Affecter les colis aux tournées de livraison | Inclus |
| Permettre aux livreurs de mettre à jour le statut depuis le navigateur du téléphone | Inclus |
| Le paiement en ligne par carte  | Exclu |
| Un programme de fidélité | Exclu |
| La tarification multi-devises | Exclu |

## 4. Demandes supplémentaires

Les fonctionnalités non décrites ci-dessus sont traitées comme des demandes de modification. Le prestataire envoie une estimation sous 2 jours ouvrables, et le travail ne commence qu’après accord écrit du client.

## 5. Exigences essentielles

- NN-1: La page d'accueil atteint un Largest Contentful Paint inférieur à 3 secondes sur une connexion 4G simulée.
- NN-2: Les mots de passe sont hachés avec Argon2id.
- NN-3: Les données personnelles sont hébergées uniquement sur des serveurs situés dans l'Union européenne.
- NN-4: La disponibilité mensuelle est d'au moins 99,9 %.

## 6. Planning et paiements

| Jalon | Échéance | Livrables | Paiement |
|---|---|---|---|
| M1 | Fin de la semaine 4 | Prototype cliquable et modèle de données | 30% |
| M2 | Fin de la semaine 9 | Parcours utilisateur principal fonctionnel en préproduction | 30% |
| M3 | Fin de la semaine 13 | Back-office, notifications et rapport de tests | 20% |
| M4 | Fin de la semaine 15 | Mise en production et documentation de passation | 20% |

## 7. Recette

Le client dispose de 5 jours ouvrables pour valider chaque jalon. Un jalon est accepté lorsqu'il ne reste aucun défaut bloquant. Chaque jalon comprend jusqu'à 3 cycles de corrections ; les cycles supplémentaires sont des demandes de modification.

## 8. Conditions juridiques et financières

| Clause | Valeur |
|---|---|
| Prix | Prix forfaitaire : 23 000 TND hors TVA |
| Factures | Les factures sont payables sous 30 jours |
| Garantie | Le prestataire corrige sans frais les défauts signalés dans les 90 jours suivant la réception finale |
| Résiliation | Chaque partie peut résilier avec un préavis écrit de 30 jours |
| Propriété intellectuelle | La propriété intellectuelle de l'application livrée est transférée au client après le paiement final |
Les parties gardent les informations confidentielles pendant 1 ans après la fin du projet.

Retard : une pénalité de 0,5 % du prix par semaine de retard s'applique, plafonnée à 10 %.

## 9. Gouvernance du projet

Un point d'avancement de 30 minutes a lieu chaque jeudi. Les décisions qui modifient le périmètre, le prix ou les délais sont confirmées par écrit.

