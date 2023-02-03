# Title     : Spatial patterns of mobility-aware social segregation
# Objective : Three regions
# Created by: Yuan Liao
# Created on: 2023-02-02

library(dplyr)
library(ggplot2)
library(ggsci)
library(ggspatial)
library(ggsn)
library(ggmap)
library(ggpubr)
library(sf)
library(geojsonsf)
library(ggraph)
library(scico)
library(scales)
library(mapdeck)
library(leaflet)
library(yaml)
library(htmlwidgets)
library(webshot2)
library(rbokeh)

keys_manager <- read_yaml('./dbs/keys.yaml')
set_token(keys_manager$maps$mapdeck)

# Static visualisation (Mobility vs. housing by region)
# region 1=Stockholm, 14=Gothenburg, 12=Malmö
geo <- geojson_sf("results/mobi_seg_spatio_static.geojson")
col2plot <- 'S_income'
geo <- geo %>% select(col2plot, deso_3) %>% rename(var=col2plot)
geo$e <- geo$var * 15000

bins <- c(seq(min(geo$var), max(geo$var), 0.1), max(geo$var))
pal <- colorBin("viridis", domain = geo$var, bins = bins)

file.url <- paste0(getwd(), "/stockholm_static_income.html")
file.png <- paste0(getwd(), "/stockholm_static_income.png")

ms <- mapdeck_style("dark")
mapdeck(style = ms, pitch = 45, zoom = 14) %>%
            add_polygon(
                data = geo[geo$deso_3 == '01',]
                , layer_id = 'seg'
                , fill_colour = 'var'
                , legend = TRUE
                , legend_options = list(digits = 5)
                , fill_opacity = 150
                , elevation = "e"
            )%>%
  mapdeck_view(
    location = c(18.063240, 59.334591),
    zoom = 7.4,
    pitch = 45
  )%>%
  saveWidget(file.url)

webshot(url=file.url,
        file=file.png,
        vwidth = 900, vheight = 900)

