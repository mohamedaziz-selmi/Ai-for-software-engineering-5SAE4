# Cahier des charges : École de langues Dar Lughat

Document d'entraînement synthétique RAFT2-P013. Le client, les personnes et les chiffres sont fictifs.

## 1. Contexte et objectifs

École de langues Dar Lughat souhaite une plateforme d'inscription aux cours. L'objectif est de ne plus gérer les inscriptions à la main et de réduire les erreurs.

## 2. Parties

Le client est École de langues Dar Lughat. Les questions sur le projet sont à adresser à pm.raft2p013@example.com ; les urgences peuvent être signalées au +216 44 895 788. Le prestataire conçoit, développe, teste et déploie l'application.

## 3. Périmètre des travaux

| Fonctionnalité | Statut |
|---|---|
| Permettre au personnel de gérer les groupes et les salles | Inclus |
| Un programme de fidélité | Exclu |
| Parcourir les cours par langue et niveau | Inclus |
| Permettre aux enseignants de saisir les présences | Inclus |
| Télécharger une attestation d'inscription en PDF | Inclus |
| La livraison à domicile | Exclu |
| Les applications mobiles natives | Exclu |
| S'inscrire dans un groupe de cours | Inclus |

## 4. Évolutions du périmètre

Toute fonctionnalité non listée dans le périmètre est une demande de modification. Le prestataire envoie une estimation sous 2 jours ouvrables, et le travail ne commence qu’après accord écrit du client.

## 5. Exigences essentielles

- NN-1: Les données personnelles sont hébergées uniquement sur des serveurs situés en Tunisie.
- NN-2: Au maximum 20 inscriptions par groupe de cours.
- NN-3: La page d'accueil atteint un Largest Contentful Paint inférieur à 3 secondes sur une connexion 4G simulée.
- NN-4: Les mots de passe sont hachés avec scrypt.

## 6. Plan de livraison

| Jalon | Échéance | Livrables | Paiement |
|---|---|---|---|
| M1 | Fin de la semaine 2 | Prototype cliquable et modèle de données | 20% |
| M2 | Fin de la semaine 5 | Parcours utilisateur principal fonctionnel en préproduction | 30% |
| M3 | Fin de la semaine 6 | Back-office, notifications et rapport de tests | 30% |
| M4 | Fin de la semaine 16 | Mise en production et documentation de passation | 20% |

## 7. Recette

Le client dispose de 7 jours ouvrables pour valider chaque jalon. Un jalon est accepté lorsqu'il ne reste aucun défaut bloquant. Chaque jalon comprend jusqu'à 3 cycles de corrections ; les cycles supplémentaires sont des demandes de modification.

## 8. Conditions commerciales

| Clause | Valeur |
|---|---|
| Prix | Prix forfaitaire : 21 500 TND hors TVA |
| Factures | Les factures sont payables sous 45 jours |
| Garantie | Le prestataire corrige sans frais les défauts signalés dans les 30 jours suivant la réception finale |
| Résiliation | Chaque partie peut résilier avec un préavis écrit de 30 jours |
| Propriété intellectuelle | La propriété intellectuelle de l'application livrée est transférée au client après le paiement final |
Les parties gardent les informations confidentielles pendant 2 ans après la fin du projet.

## 9. Réunions

Un point d'avancement de 60 minutes a lieu chaque lundi. Les décisions qui modifient le périmètre, le prix ou les délais sont confirmées par écrit.

