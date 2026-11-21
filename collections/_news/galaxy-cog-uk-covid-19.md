---
title: "Galaxy Europe monitor COG-UK COVID-19 genomic data"
date: 2021-04-23
standfirst: "Galaxy Europe has started to monitor COG-UK data. COG-UK is the COVID-19 Genomics UK Consortium, which was set up in 2020 in response to the Coronavirus pandemic. The consortium sequences SARS-CoV-2 genomes, providing vi"
excerpt: ""
categories: News
wpId: 19588
image: "https://elixiruknode.org/wp-content/uploads/2024/03/banner-workflow.webp"
related:
  activities: ["galaxy-community"]
  services: ["workflowhub"]
---

[Galaxy Europe](https://usegalaxy.eu/) has started to monitor COG-UK data. [COG-UK](https://www.cogconsortium.uk/) is the COVID-19 Genomics UK Consortium, which was set up in 2020 in response to the Coronavirus pandemic.  The consortium sequences SARS-CoV-2 genomes, providing vital information on the transmission and tracking of viral variants. This work has been crucial in the UK’s response to the pandemic and to our ability to identify and track new variants with such success.

Galaxy Europe is now able to use this database to monitor the genomes being sequenced for important data such as provenance and variants present. The protocol means that new samples in the database are processed every three hours, and the results are then put into public storage and integrated into [Beacon](https://covid19beacon.crg.eu/) by the Centre of Genomic Regulation. Beacon is an ELIXIR tool to find SARS-CoV-2 variability at genomic, amino acid and motif levels and allows researchers to search for things such as specific genomic variants and explore the associated metadata.

[WorkflowHub](https://workflowhub.eu/), another project in which ELIXIR-UK is heavily involved, hosts the publicly validated workflows that this project uses. When producing publicly available data, it is important that the whole process is well documented in order for the results to be trusted and reproducible, so WorkflowHub plays an important role in this project.

The workflows produced during this project can be used to process samples from other countries, and Galaxy Europe is offering to help set this up for other countries as a next step in monitoring SARS-CoV-2 genomic data. This continuous analysis system is automated using the BioBlend software library, which is maintained at the Earlham Institute, one of the ELIXIR-UK member organisations.

The team behind this project have also provided the resources for people who don’t use Galaxy to contribute via a [simple GitHub](https://github.com/usegalaxy-eu/sars-cov-2-processing-requests). This should make it easy for people to analyse viral sequences even if they don’t want to run their own workflows.

All through the Coronavirus pandemic, there has been a clear need for high-quality genomic data and associated metadata, which is freely available for researchers working in this area. It has enabled the tracking of transmission in care homes and hospitals and allowed the early identification of new strains. The UK has led the way in this area, and the data we have produced is now being used to demonstrate this new way of monitoring the data from Galaxy Europe.

- [Documented process](https://github.com/usegalaxy-eu/ena-cog-uk-wfs/blob/main/docs/manual.md)
- [Validated workflows](https://www.biorxiv.org/content/10.1101/2021.03.25.437046v1)
- [Summary of processed data](https://observablehq.com/@spond/sars-cov-2-cog-uk)
