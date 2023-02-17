# Title     : Visiting vs. housing segregation on
# Objective : Value difference on maps
# Created by: Yuan Liao
# Created on: 2023-2-3

library(dplyr)
library(ggplot2)
library(ggpubr)
library(sf)
library(geojsonsf)
library(ggdensity)
library(yaml)
library(DBI)
options(scipen=10000)

# Residential segregation
keys_manager <- read_yaml('./dbs/keys.yaml')
user <- keys_manager$database$user
password <- keys_manager$database$password
port <- keys_manager$database$port
db_name <- keys_manager$database$name
con <- DBI::dbConnect(RPostgres::Postgres(),
                      host = "localhost",
                      dbname = db_name,
                      user = user,
                      password = password,
                      port = port)
df <- dbGetQuery(con, 'SELECT * FROM segregation.indi_mobi_resi_seg_metrics_zone')
df <- df %>%
  rename('Foreign_background'='Foreign background',
         'Lowest_income_group'='Lowest income group') %>%
  select(Foreign_background, Lowest_income_group, evenness_income, radius_of_gyration)

# Static visualisation (Mobility vs. housing by region)
# region 1=Stockholm, 14=Gothenburg, 12=Malmö
geo <- geojson_sf("results/mobi_seg_spatio_static.geojson")
geo <- geo %>%
  filter(weekday==1,
         holiday==0) %>%
  rename('Foreign_background'='Foreign background',
         'Not_Sweden'='Not Sweden',
         'Lowest_income_group'='Lowest income group',
         'Foreign_background_h'='Foreign background_h',
         'Not_Sweden_h'='Not Sweden_h',
         'Lowest_income_group_h'='Lowest income group_h')

fb.tre <- 0.25
df.h.l <- df[df$Lowest_income_group > fb.tre,]
df.h.h <- geo[geo$Lowest_income_group_h <= fb.tre, ]

df.v.l <- geo[geo$Lowest_income_group > fb.tre,
              c('evenness_income', 'Foreign_background', 'radius_of_gyration')]

df.v.h <- geo[geo$Lowest_income_group <= fb.tre,
              c('evenness_income', 'Foreign_background', 'radius_of_gyration')]

ethni.seg.plot <- function(data.low, data.high, pt.size){
  g1 <- ggplot(data=data.low, aes(x=Foreign_background, y=evenness_income)) +
    geom_hdr(fill='orange', show.legend = F) +
    geom_point(color='orange', size=pt.size) +
    xlim(0, 1) +
    ylim(0, 0.6) +
    labs(title = 'Share of lowest-income group > 25%', y = 'Unevenness of income', x = 'Share of foreign background') +
    theme_minimal()

  g2 <- ggplot(data=data.high, aes(x=Foreign_background, y=evenness_income)) +
    geom_hdr(fill='steelblue', show.legend = F) +
    geom_point(color='steelblue', size=pt.size) +
    xlim(0, 1) +
    ylim(0, 0.6) +
    labs(title = '<= 25%', y = '', x = 'Share of foreign background') +
    theme_minimal()

  G <- ggarrange(g1, g2, ncol = 2, nrow = 1)
  return(G)
}

rg.seg.plot <- function(data.low, data.high, pt.size){
  g1 <- ggplot(data=data.low, aes(x=radius_of_gyration, y=evenness_income)) +
    geom_hdr(fill='orange', show.legend = F) +
    geom_point(color='orange', size=pt.size) +
    scale_x_log10(limits=c(0.1, 1000)) +
    ylim(0, 0.6) +
    labs(title = 'Share of lowest-income group > 25%', y = 'Unevenness of income', x = 'Radius of gyration (km)') +
    theme_minimal()

  g2 <- ggplot(data=data.high, aes(x=radius_of_gyration, y=evenness_income)) +
    geom_hdr(fill='steelblue', show.legend = F) +
    geom_point(color='steelblue', size=pt.size) +
    scale_x_log10(limits=c(0.1, 1000)) +
    ylim(0, 0.6) +
    labs(title = '<= 25%', y = '', x = 'Radius of gyration (km)') +
    theme_minimal()

  G <- ggarrange(g1, g2, ncol = 2, nrow = 1)
  return(G)
}

G <- ggarrange(ethni.seg.plot(df.v.l, df.v.h, 0.8),
               rg.seg.plot(df.v.l, df.v.h, 0.8),
               ncol = 1, nrow = 2, labels = c('(a)', '(b)'))
ggsave(filename = paste0("figures/", 'mobi_seg_inc_relations_v.png'), plot=G,
       width = 8, height = 8, unit = "in", dpi = 300)

G2 <- ggarrange(ethni.seg.plot(df.h.l, df.h.h, 0.4),
               rg.seg.plot(df.h.l, df.h.h, 0.4),
               ncol = 1, nrow = 2, labels = c('(a)', '(b)'))
ggsave(filename = paste0("figures/", 'mobi_seg_inc_relations_h.png'), plot=G2,
       width = 8, height = 8, unit = "in", dpi = 300)
