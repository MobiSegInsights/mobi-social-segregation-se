# Title     : Spatial patterns of mobility-aware social segregation
# Objective : Three regions
# Created by: Yuan Liao
# Created on: 2023-02-15

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

segregation.mapping <- function(geo2plot, var, vname, bmap){
  g1 <- ggmap(bmap) +
    geom_sf(data=geo2plot, aes_string(fill=var), inherit.aes = FALSE,
            color = NA, alpha=0.7, show.legend = T)
  g2 <- ggmap(bmap) +
    geom_sf(data=geo2plot, aes_string(fill=paste0(var, '_h')), inherit.aes = FALSE,
            color = NA, alpha=0.7, show.legend = T)
  if (var == 'radius_of_gyration'){
    g1 <- g1 +
      scale_fill_gradient(low = "cyan3", high = "coral2", name=vname) # , trans = "log"
    g2 <- g2 +
      scale_fill_gradient(low = "cyan3", high = "coral2", name=vname) #, trans = "log"
  } else {
    g1 <- g1 +
      scale_fill_gradient(low = "cyan3", high = "coral2", name=vname)
    g2 <- g2 +
      scale_fill_gradient(low = "cyan3", high = "coral2", name=vname)
  }
  g1 <- g1 +
    labs(title = 'Visiting') +
    theme_void() +
    theme(legend.position = 'top', legend.key.height = unit(0.2, "cm"),
          plot.margin = margin(0,0.2,0.2,0, "cm"))
  g2 <- g2 +
    labs(title = 'Housing') +
    theme_void() +
    theme(legend.position = 'top', legend.key.height = unit(0.2, "cm"),
          plot.margin = margin(0,0.2,0.2,0, "cm"))

  G <- ggarrange(g1, g2, ncol = 2, nrow = 1, common.legend = T, legend="top")
  return(G)
}

vars <- c('Unevenness of income', 'Lowest income group', 'Foreign background', "Radius of gyration (km)")
names(vars) <- c('evenness_income', "Lowest_income_group", "Foreign_background", "radius_of_gyration")

regions <- c('Stockholm', 'Gothenburg', 'Malmo')
names(regions) <- c('01', '14', '12')

# Weekday, non-holiday

for (r in names(regions)){
  geo2plot <- map.select(geo=geo, w=1, h=0, r=r)
  bmap <- get.basemap(geo2plot)
  g.list <- lapply(names(vars), function(x){segregation.mapping(geo=geo2plot, var=x,
                                                                vname=vars[[x]], bmap=bmap)})
  G <- ggarrange(plotlist=g.list, ncol = 2, nrow = 2, labels = c('(a)', '(b)', '(c)', '(d)'))
  ggsave(filename = paste0("figures/spatio_static_", regions[[r]], ".png"), plot=G,
         width = 7.5, height = 5, unit = "in", dpi = 300)
}

