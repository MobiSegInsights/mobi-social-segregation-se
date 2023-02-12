# Title     : Spatial patterns of mobility-aware social segregation
# Objective : Three regions
# Created by: Yuan Liao
# Created on: 2023-02-03

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
options(scipen=10000)

# Static visualisation (Mobility vs. housing by region)
# region 1=Stockholm, 14=Gothenburg, 12=Malmö
geo <- geojson_sf("results/mobi_seg_spatio_static.geojson")
geo <- geo %>%
  rename('Foreign_background'='Foreign background',
         'Not_Sweden'='Not Sweden',
         'Lowest_income_group'='Lowest income group',
         'Foreign_background_h'='Foreign background_h',
         'Not_Sweden_h'='Not Sweden_h',
         'Lowest_income_group_h'='Lowest income group_h')

map.select <- function(geo, w, h, r){
  map2plot <- geo %>%
    filter(weekday==w,
           holiday==h,
           deso_3==r)
  return(map2plot)
}

get.basemap <- function(geoframe){
  # Get basemap as the background
  bbox <- st_bbox(geoframe)
  names(bbox) <- c("left", "bottom", "right", "top")
  bmap <- get_stamenmap(bbox, maptype="toner-lite", zoom = 10)
  return(bmap)
}

segregation.mapping <- function(geo2plot, var, vname, fname, bmap){
  g1 <- ggmap(bmap) +
    geom_sf(data=geo2plot, aes_string(fill=var), inherit.aes = FALSE,
            color = NA, alpha=0.7, show.legend = T) +
    scale_fill_gradient(low = "green", high = "red", name=vname) +
    theme_void() +
    theme(legend.position = 'bottom',
          plot.margin = margin(0,0,0,0, "cm"))

  fill_var.h <- shQuote(paste0(var, '_h'))
  g2 <- ggmap(bmap) +
    geom_sf(data=geo2plot, aes_string(fill=paste0(var, '_h')), inherit.aes = FALSE,
            color = NA, alpha=0.7, show.legend = T) +
    scale_fill_gradient(low = "green", high = "red", name=vname) +
    theme_void() +
    theme(legend.position = 'bottom',
          plot.margin = margin(0,0,0,0, "cm"))

  G <- ggarrange(g1, g2, ncol = 2, nrow = 1, labels = c('Visiting', 'Housing'),
                  common.legend = T, legend="top")
  ggsave(filename = paste0("figures/", fname), plot=G,
         width = 8, height = 5, unit = "in", dpi = 300)
}

vars <- c('Unevenness of income', 'Unevenness of birth region', 'Unevenness of foreign background',
          'Foreign background', 'Not Sweden', 'Lowest income group')
names(vars) <- c('evenness_income', 'evenness_birth_region', 'evenness_background',
                 "Foreign_background", "Not_Sweden", "Lowest_income_group")

regions <- c('Stockholm', 'Gothenburg', 'Malmo')
names(regions) <- c('01', '14', '12')

# Weekday, non-holiday
for (r in names(regions)){
  geo2plot <- map.select(geo=geo, w=1, h=0, r=r)
  bmap <- get.basemap(geo2plot)
  for (v in names(vars)){
    fig.name <- paste0('spatial_static_', regions[[r]], '_', vars[[v]], '.png')
    segregation.mapping(geo=geo2plot, var=v, vname=vars[[v]], fname=fig.name, bmap=bmap)
  }
}
