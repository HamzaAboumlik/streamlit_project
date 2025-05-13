CREATE TABLE [dbo].[Direction] (
    [ID_Direction] [bigint] IDENTITY(1,1) NOT NULL,
    [Direction_Direction] [varchar](50) NULL,
    CONSTRAINT [PK_Direction] PRIMARY KEY CLUSTERED ([ID_Direction] ASC)
) ON [PRIMARY];

CREATE TABLE [dbo].[Service] (
    [ID_Service] [bigint] IDENTITY(1,1) NOT NULL,
    [Service_Service] [varchar](50) NULL,
    CONSTRAINT [PK_Service] PRIMARY KEY CLUSTERED ([ID_Service] ASC)
) ON [PRIMARY];

CREATE TABLE [dbo].[Employe] (
    [ID_Employe] [bigint] IDENTITY(1,1) NOT NULL,
    [Code_Employe] [varchar](10) NULL,
    [Badge_Employe] [varchar](10) NULL,
    [CIN_Employe] [varchar](10) NULL,
    [Nom_Employe] [varchar](40) NULL,
    [Prenom_Employe] [varchar](40) NULL,
    [Fonction_Employe] [varchar](40) NULL,
    [ID_Service] [bigint] NULL,
    [ID_Direction] [bigint] NULL,
    [Affectation_Employe] [varchar](30) NULL,
    [Statut_Employe] [varchar](20) NULL,
    [Date_Sortie_Employe] [varchar](25) NULL,
    CONSTRAINT [PK_Employe] PRIMARY KEY CLUSTERED ([ID_Employe] ASC),
    CONSTRAINT [FK_Employe_Service] FOREIGN KEY ([ID_Service]) REFERENCES [dbo].[Service] ([ID_Service]),
    CONSTRAINT [FK_Employe_Direction] FOREIGN KEY ([ID_Direction]) REFERENCES [dbo].[Direction] ([ID_Direction])
) ON [PRIMARY];

CREATE TABLE [dbo].[Article] (
    [ID_Article] [bigint] IDENTITY(1,1) NOT NULL,
    [Ref_Article] [varchar](20) NULL,
    [Libelle_Article] [varchar](50) NULL,
    [Type_Article] [varchar](50) NULL,
    [Categorie_Article] [varchar](50) NULL,
    [Marque_Article] [varchar](40) NULL,
    [Description_Article] [varchar](450) NULL,
    [Date_Achat_Article] [varchar](10) NULL,
    [Date_Echeance_Article] [varchar](10) NULL,
    [Etat_Article] [varchar](20) NULL,
    [Statut_Article] [varchar](20) NULL CONSTRAINT [DF_Article_Statut_Article] DEFAULT ('NON AFFECTE'),
    [Location_Article] [varchar](3) NULL,
    [Affecter_au_Article] [varchar](3) NULL,
    [Service_Employe_Article] [varchar](40) NULL,
    [Agence_Article] [varchar](20) NULL,
    [Date_Affectation_Article] [varchar](10) NULL,
    [Date_Restitution_Article] [varchar](10) NULL,
    [Compte_Comptable_Article] [varchar](10) NULL,
    [modifier_o] [varchar](2) NULL,
    [Achete_Par_Article] [varchar](40) NULL,
    [Affecte_A_Article] [varchar](40) NULL,
    [Numero_Affectation] [bigint] NULL,
    [image_path] [varchar](255) NULL,
    CONSTRAINT [PK_Article] PRIMARY KEY CLUSTERED ([ID_Article] ASC)
) ON [PRIMARY];

CREATE TABLE [dbo].[Affectation] (
    [ID_Affectation] [bigint] IDENTITY(1,1) NOT NULL,
    [ID_Article_Affectation] [bigint] NULL,
    [ID_Employe] [bigint] NULL,
    [Service_Employe_Article] [varchar](40) NULL,
    [Date_Affectation] [varchar](10) NULL,
    [Date_Restitution_Affectation] [varchar](10) NULL,
    [Affecter_au_Article] [varchar](3) NULL,
    [Numero_Affectation] [bigint] NULL,
    [Notification_Sent] [bit] NOT NULL CONSTRAINT [DF_Affectation_Notification_Sent] DEFAULT (0),
    CONSTRAINT [PK_Affectation] PRIMARY KEY CLUSTERED ([ID_Affectation] ASC),
    CONSTRAINT [FK_Affectation_Article] FOREIGN KEY ([ID_Article_Affectation]) REFERENCES [dbo].[Article] ([ID_Article]),
    CONSTRAINT [FK_Affectation_Employe] FOREIGN KEY ([ID_Employe]) REFERENCES [dbo].[Employe] ([ID_Employe])
) ON [PRIMARY];

CREATE TABLE [dbo].[User] (
    [id_user] [bigint] IDENTITY(1,1) NOT NULL,
    [email] [varchar](100) NOT NULL,
    [password] [varchar](100) NOT NULL,
    CONSTRAINT [PK_User] PRIMARY KEY CLUSTERED ([id_user] ASC),
    CONSTRAINT [UQ_User_Email] UNIQUE ([email])
) ON [PRIMARY];

CREATE TABLE [dbo].[Backup_Log] (
    [ID_Backup] [bigint] IDENTITY(1,1) NOT NULL,
    [Backup_Date] [datetime] NOT NULL CONSTRAINT [DF_Backup_Log_Backup_Date] DEFAULT (GETDATE()),
    [Backup_Status] [varchar](20) NOT NULL,
    [Backup_Details] [varchar](255) NULL,
    CONSTRAINT [PK_Backup_Log] PRIMARY KEY CLUSTERED ([ID_Backup] ASC)
) ON [PRIMARY];