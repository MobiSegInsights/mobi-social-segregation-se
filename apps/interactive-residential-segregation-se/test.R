library(leaflet)
library(dplyr)
library(sf)
library(ggplot2)
library(ggmap)
library(ggsn)
library(mapdeck)
library(geojsonsf)


zones <- geojson_sf("InteractiveResiSegSweden/data/residential_income_segregation.geojson")
zones2 <- geojson_sf("InteractiveResiSegSweden/data/mobi_seg_spatio_static.geojson")

col2plot <- 'evenness_income'
zones2plot <- zones %>% select(col2plot) %>% rename(var=col2plot)
bins <- c(seq(min(zones2plot$var), max(zones2plot$var), 0.1), max(zones2plot$var))
pal <- colorBin("viridis", domain = zones2plot$var, bins = bins)

mapdeck(token = "pk.eyJ1IjoieXVhbmxpYW8iLCJhIjoiY2xkMGl6bGw1MWRqODNycDdiMmdoMzR1eSJ9.cW2c9yeQZG27b8Z37EUeVg", 
        style = mapdeck_style("dark")) %>%
  add_polygon(
    data = zones
    , layer = "polygon_layer"
    , fill_colour = "Lowest income group"
    , legend = TRUE
  )
