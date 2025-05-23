USE [master]
GO
/****** Object:  Database [gestion_parc_informatique]    Script Date: 5/19/2025 10:35:43 PM ******/
CREATE DATABASE [gestion_parc_informatique]
 CONTAINMENT = NONE
 ON  PRIMARY 
( NAME = N'gestion_parc_informatique', FILENAME = N'C:\Program Files\Microsoft SQL Server\MSSQL12.TEST\MSSQL\DATA\gestion_parc_informatique.mdf' , SIZE = 5120KB , MAXSIZE = UNLIMITED, FILEGROWTH = 1024KB )
 LOG ON 
( NAME = N'gestion_parc_informatique_log', FILENAME = N'C:\Program Files\Microsoft SQL Server\MSSQL12.TEST\MSSQL\DATA\gestion_parc_informatique_log.ldf' , SIZE = 2048KB , MAXSIZE = 2048GB , FILEGROWTH = 10%)
GO
ALTER DATABASE [gestion_parc_informatique] SET COMPATIBILITY_LEVEL = 120
GO
IF (1 = FULLTEXTSERVICEPROPERTY('IsFullTextInstalled'))
begin
EXEC [gestion_parc_informatique].[dbo].[sp_fulltext_database] @action = 'enable'
end
GO
ALTER DATABASE [gestion_parc_informatique] SET ANSI_NULL_DEFAULT OFF 
GO
ALTER DATABASE [gestion_parc_informatique] SET ANSI_NULLS OFF 
GO
ALTER DATABASE [gestion_parc_informatique] SET ANSI_PADDING OFF 
GO
ALTER DATABASE [gestion_parc_informatique] SET ANSI_WARNINGS OFF 
GO
ALTER DATABASE [gestion_parc_informatique] SET ARITHABORT OFF 
GO
ALTER DATABASE [gestion_parc_informatique] SET AUTO_CLOSE OFF 
GO
ALTER DATABASE [gestion_parc_informatique] SET AUTO_SHRINK OFF 
GO
ALTER DATABASE [gestion_parc_informatique] SET AUTO_UPDATE_STATISTICS ON 
GO
ALTER DATABASE [gestion_parc_informatique] SET CURSOR_CLOSE_ON_COMMIT OFF 
GO
ALTER DATABASE [gestion_parc_informatique] SET CURSOR_DEFAULT  GLOBAL 
GO
ALTER DATABASE [gestion_parc_informatique] SET CONCAT_NULL_YIELDS_NULL OFF 
GO
ALTER DATABASE [gestion_parc_informatique] SET NUMERIC_ROUNDABORT OFF 
GO
ALTER DATABASE [gestion_parc_informatique] SET QUOTED_IDENTIFIER OFF 
GO
ALTER DATABASE [gestion_parc_informatique] SET RECURSIVE_TRIGGERS OFF 
GO
ALTER DATABASE [gestion_parc_informatique] SET  DISABLE_BROKER 
GO
ALTER DATABASE [gestion_parc_informatique] SET AUTO_UPDATE_STATISTICS_ASYNC OFF 
GO
ALTER DATABASE [gestion_parc_informatique] SET DATE_CORRELATION_OPTIMIZATION OFF 
GO
ALTER DATABASE [gestion_parc_informatique] SET TRUSTWORTHY OFF 
GO
ALTER DATABASE [gestion_parc_informatique] SET ALLOW_SNAPSHOT_ISOLATION OFF 
GO
ALTER DATABASE [gestion_parc_informatique] SET PARAMETERIZATION SIMPLE 
GO
ALTER DATABASE [gestion_parc_informatique] SET READ_COMMITTED_SNAPSHOT OFF 
GO
ALTER DATABASE [gestion_parc_informatique] SET HONOR_BROKER_PRIORITY OFF 
GO
ALTER DATABASE [gestion_parc_informatique] SET RECOVERY SIMPLE 
GO
ALTER DATABASE [gestion_parc_informatique] SET  MULTI_USER 
GO
ALTER DATABASE [gestion_parc_informatique] SET PAGE_VERIFY CHECKSUM  
GO
ALTER DATABASE [gestion_parc_informatique] SET DB_CHAINING OFF 
GO
ALTER DATABASE [gestion_parc_informatique] SET FILESTREAM( NON_TRANSACTED_ACCESS = OFF ) 
GO
ALTER DATABASE [gestion_parc_informatique] SET TARGET_RECOVERY_TIME = 0 SECONDS 
GO
ALTER DATABASE [gestion_parc_informatique] SET DELAYED_DURABILITY = DISABLED 
GO
USE [gestion_parc_informatique]
GO
/****** Object:  Table [dbo].[Affectation]    Script Date: 5/19/2025 10:35:43 PM ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
SET ANSI_PADDING ON
GO
CREATE TABLE [dbo].[Affectation](
	[ID_Affectation] [bigint] IDENTITY(1,1) NOT NULL,
	[ID_Article_Affectation] [bigint] NULL,
	[Service_Employe_Article] [varchar](100) NULL,
	[Date_Restitution_Affectation] [date] NULL,
	[Affecter_au_Article] [varchar](50) NULL,
	[Numero_Affectation] [varchar](20) NULL,
	[ID_Employe] [bigint] NULL,
	[Date_Affectation] [date] NULL,
 CONSTRAINT [PK_Affectation] PRIMARY KEY CLUSTERED 
(
	[ID_Affectation] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON) ON [PRIMARY]
) ON [PRIMARY]

GO
SET ANSI_PADDING OFF
GO
/****** Object:  Table [dbo].[Article]    Script Date: 5/19/2025 10:35:43 PM ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
SET ANSI_PADDING ON
GO
CREATE TABLE [dbo].[Article](
	[ID_Article] [bigint] IDENTITY(1,1) NOT NULL,
	[Ref_Article] [varchar](20) NULL,
	[Libelle_Article] [varchar](50) NULL,
	[Type_Article] [varchar](50) NULL,
	[Categorie_Article] [varchar](50) NULL,
	[Marque_Article] [varchar](40) NULL,
	[Description_Article] [varchar](450) NULL,
	[Etat_Article] [varchar](20) NULL,
	[Statut_Article] [varchar](20) NULL CONSTRAINT [DF_Article_Statut_Article]  DEFAULT ('NON AFFECTE'),
	[Location_Article] [varchar](3) NULL,
	[Affecter_au_Article] [varchar](50) NULL,
	[Service_Employe_Article] [varchar](100) NULL,
	[Agence_Article] [varchar](20) NULL,
	[Date_Restitution_Article] [date] NULL,
	[Compte_Comptable_Article] [varchar](10) NULL,
	[modifier_o] [varchar](2) NULL,
	[Achete_Par_Article] [varchar](40) NULL,
	[Affecte_A_Article] [varchar](40) NULL,
	[Numero_Affectation] [varchar](20) NULL,
	[Date_Achat_Article] [date] NULL,
	[Date_Echeance_Article] [date] NULL,
	[Date_Affectation_Article] [date] NULL,
	[Image_Path] [varchar](255) NULL,
 CONSTRAINT [PK_Article] PRIMARY KEY CLUSTERED 
(
	[ID_Article] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON) ON [PRIMARY]
) ON [PRIMARY]

GO
SET ANSI_PADDING OFF
GO
/****** Object:  Table [dbo].[Direction]    Script Date: 5/19/2025 10:35:43 PM ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
SET ANSI_PADDING ON
GO
CREATE TABLE [dbo].[Direction](
	[ID_Direction] [bigint] IDENTITY(1,1) NOT NULL,
	[Direction_Direction] [varchar](50) NULL,
 CONSTRAINT [PK_Direction] PRIMARY KEY CLUSTERED 
(
	[ID_Direction] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON) ON [PRIMARY]
) ON [PRIMARY]

GO
SET ANSI_PADDING OFF
GO
/****** Object:  Table [dbo].[Employe]    Script Date: 5/19/2025 10:35:43 PM ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
SET ANSI_PADDING ON
GO
CREATE TABLE [dbo].[Employe](
	[ID_Employe] [bigint] IDENTITY(1,1) NOT NULL,
	[Code_Employe] [varchar](10) NULL,
	[Badge_Employe] [varchar](10) NULL,
	[CIN_Employe] [varchar](10) NULL,
	[Nom_Employe] [varchar](40) NULL,
	[Prenom_Employe] [varchar](40) NULL,
	[Fonction_Employe] [varchar](40) NULL,
	[Service_Employe] [varchar](40) NULL,
	[Direction_Employe] [varchar](40) NULL,
	[Affectation_Employe] [varchar](30) NULL,
	[Statut_Employe] [varchar](20) NULL,
	[Date_Sortie_Employe] [varchar](25) NULL,
 CONSTRAINT [PK_Employe] PRIMARY KEY CLUSTERED 
(
	[ID_Employe] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON) ON [PRIMARY]
) ON [PRIMARY]

GO
SET ANSI_PADDING OFF
GO
/****** Object:  Table [dbo].[Service]    Script Date: 5/19/2025 10:35:43 PM ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
SET ANSI_PADDING ON
GO
CREATE TABLE [dbo].[Service](
	[ID_Service] [bigint] IDENTITY(1,1) NOT NULL,
	[Service_Service] [varchar](50) NULL,
 CONSTRAINT [PK_Service] PRIMARY KEY CLUSTERED 
(
	[ID_Service] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON) ON [PRIMARY]
) ON [PRIMARY]

GO
SET ANSI_PADDING OFF
GO
/****** Object:  Table [dbo].[User]    Script Date: 5/19/2025 10:35:43 PM ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
SET ANSI_PADDING ON
GO
CREATE TABLE [dbo].[User](
	[ID_User] [bigint] IDENTITY(1,1) NOT NULL,
	[Email] [varchar](100) NOT NULL,
	[Password] [varchar](256) NOT NULL,
	[Role] [varchar](20) NULL DEFAULT ('user'),
 CONSTRAINT [PK_User] PRIMARY KEY CLUSTERED 
(
	[ID_User] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON) ON [PRIMARY],
UNIQUE NONCLUSTERED 
(
	[Email] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON) ON [PRIMARY]
) ON [PRIMARY]

GO
SET ANSI_PADDING OFF
GO
ALTER TABLE [dbo].[Affectation]  WITH CHECK ADD  CONSTRAINT [FK_Affectation_Employe] FOREIGN KEY([ID_Employe])
REFERENCES [dbo].[Employe] ([ID_Employe])
GO
ALTER TABLE [dbo].[Affectation] CHECK CONSTRAINT [FK_Affectation_Employe]
GO
USE [master]
GO
ALTER DATABASE [gestion_parc_informatique] SET  READ_WRITE 
GO
