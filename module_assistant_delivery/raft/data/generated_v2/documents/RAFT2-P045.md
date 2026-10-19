# Cahier des charges : Médiathèque Ennour

Document d'entraînement synthétique RAFT2-P045. Le client, les personnes et les chiffres sont fictifs.

## 1. Objet du projet

Aujourd'hui, Médiathèque Ennour gère ses prêts avec des tableurs et des appels téléphoniques. Ce projet livre une application de gestion des prêts de livres.

## 2. Parties et contacts

Le client est Médiathèque Ennour. L'adresse de contact projet du client est pm.raft2p045@example.com ; les urgences peuvent être signalées au +216 48 479 223. Le prestataire conçoit, développe, teste et déploie l'application.

## 3. Périmètre

| Fonctionnalité | Statut |
|---|---|
| La migration des données historiques | Exclu |
| Prolonger un prêt en ligne une fois | Inclus |
| Rechercher dans le catalogue par titre, auteur ou sujet | Inclus |
| Envoyer des rappels de retard par e-mail | Inclus |
| La tarification multi-devises | Exclu |
| Le paiement en ligne par carte  | Exclu |
| Afficher les statistiques mensuelles de prêts | Inclus |
| Permettre aux bibliothécaires d'enregistrer les retours avec un lecteur de code-barres | Inclus |

## 4. Évolutions du périmètre

Toute fonctionnalité non listée dans le périmètre est une demande de modification. Le prestataire envoie une estimation sous 5 jours ouvrables, et le travail ne commence qu’après accord écrit du client.

## 5. Exigences essentielles

- NN-1: Les pages destinées aux clients respectent le WCAG 2.1 niveau AA.
- NN-2: Les mots de passe sont hachés avec bcrypt.
- NN-3: Les données personnelles sont hébergées uniquement sur des serveurs situés dans l'Union européenne.
- NN-4: Au maximum 25 prêts par carte de membre.

## 6. Jalons et paiements

| Jalon | Échéance | Livrables | Paiement |
|---|---|---|---|
| M1 | Fin de la semaine 2 | Prototype cliquable et modèle de données | 25% |
| M2 | Fin de la semaine 11 | Parcours utilisateur principal fonctionnel en préproduction | 25% |
| M3 | Fin de la semaine 13 | Back-office, notifications et rapport de tests | 25% |
| M4 | Fin de la semaine 19 | Mise en production et documentation de passation | 25% |

## 7. Validation des jalons

Le client dispose de 10 jours ouvrables pour valider chaque jalon. Un jalon est accepté lorsqu'il ne reste aucun défaut bloquant. Chaque jalon comprend jusqu'à 1 cycles de corrections ; les cycles supplémentaires sont des demandes de modification.

## 8. Conditions commerciales

| Clause | Valeur |
|---|---|
| Prix | Prix forfaitaire : 36 500 TND hors TVA |
| Factures | Les factures sont payables sous 30 jours |
| Garantie | Le prestataire corrige sans frais les défauts signalés dans les 60 jours suivant la réception finale |
| Résiliation | Chaque partie peut résilier avec un préavis écrit de 15 jours |
| Propriété intellectuelle | La propriété intellectuelle de l'application livrée est transférée au client après le paiement final |
Les parties gardent les informations confidentielles pendant 2 ans après la fin du projet.

Retard : une pénalité de 1 % du prix par semaine de retard s'applique, plafonnée à 10 %.

## 9. Réunions

Un point d'avancement de 45 minutes a lieu chaque lundi. Les décisions qui modifient le périmètre, le prix ou les délais sont confirmées par écrit.

