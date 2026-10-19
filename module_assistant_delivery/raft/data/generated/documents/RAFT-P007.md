# Cahier des charges : École de langues Dar Lughat

Document d'entraînement synthétique RAFT-P007. Le client, les personnes et les chiffres sont fictifs.

## 1. Contexte et objectifs

École de langues Dar Lughat souhaite une plateforme d'inscription aux cours. L'objectif est de remplacer la gestion manuelle des inscriptions et de réduire les erreurs.

## 2. Parties

Le client est École de langues Dar Lughat. L'adresse de contact projet du client est pm.raftp007@example.com, et le numéro pour les urgences est +216 69 158 187. Le prestataire conçoit, développe, teste et déploie l'application.

## 3. Périmètre

### 3.1 Inclus

- Les utilisateurs peuvent permettre aux enseignants de saisir les présences.
- Les utilisateurs peuvent permettre au personnel de gérer les groupes et les salles.
- Les utilisateurs peuvent télécharger une attestation d'inscription en PDF.
- Les utilisateurs peuvent passer un test de niveau en ligne.
- Les utilisateurs peuvent parcourir les cours par langue et niveau.

### 3.2 Exclus

- La tarification multi-devises.
- La livraison à domicile.
- Le paiement en ligne par carte ; les clients paient sur place.

### 3.3 Demandes de modification

Toute fonctionnalité non listée dans la section 3.1 est une demande de modification. Le prestataire envoie une estimation sous 5 jours ouvrables, et le travail ne commence qu'après accord écrit du client.

## 4. Exigences non négociables

- NN-1: Au maximum 20 inscriptions par groupe de cours.
- NN-2: Les mots de passe sont hachés avec bcrypt.
- NN-3: Aucune donnée personnelle n'apparaît dans les journaux de l'application.
- NN-4: La page d'accueil atteint un Largest Contentful Paint inférieur à 3 secondes sur une connexion 4G simulée.

## 5. Jalons et paiements

- M1, à livrer à la fin de la semaine 6 : prototype cliquable et modèle de données. Paiement : 30 % du prix.
- M2, à livrer à la fin de la semaine 11 : parcours utilisateur principal fonctionnel en préproduction. Paiement : 30 % du prix.
- M3, à livrer à la fin de la semaine 14 : back-office, notifications et rapport de tests. Paiement : 20 % du prix.
- M4, à livrer à la fin de la semaine 15 : mise en production et documentation de passation. Paiement : 20 % du prix.

## 6. Recette

Le client dispose de 5 jours ouvrables pour valider chaque jalon. Un jalon est accepté lorsqu'il ne reste aucun défaut bloquant. Chaque jalon comprend jusqu'à 1 cycles de corrections ; les cycles supplémentaires sont des demandes de modification.

## 7. Conditions contractuelles

- Prix forfaitaire : 25 000 TND hors TVA, payé par jalon selon la section 5. Les factures sont payables sous 30 jours.
- La propriété intellectuelle de l'application livrée est transférée au client après le paiement final.
- Garantie: le prestataire corrige sans frais les défauts signalés dans les 60 jours suivant la réception finale.
- Résiliation: chaque partie peut résilier avec un préavis écrit de 15 jours.
- Confidentialité : les parties gardent les informations confidentielles pendant 1 ans après la fin du projet.

## 8. Communication

Un point d'avancement de 60 minutes a lieu chaque lundi. Les décisions qui modifient le périmètre, le prix ou les délais sont confirmées par écrit.

