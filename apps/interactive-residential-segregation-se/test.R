library(leaflet)
library(dplyr)
library(sf)
library(ggplot2)
library(ggmap)
library(ggsn)
library(mapdeck)

zones <- st_transform(st_read('InteractiveResiSegSweden/data/resi_segregation.shp'), crs = 4326)
col2plot <- 'S_inc'
zones2plot <- zones %>% select(col2plot) %>% rename(var=col2plot)
bins <- c(seq(min(zones2plot$var), max(zones2plot$var), 0.1), max(zones2plot$var))
pal <- colorBin("viridis", domain = zones2plot$var, bins = bins)
zones2plot %>%
  leaflet() %>%
  addTiles() %>%
  addPolygons(fillColor = ~pal(var), opacity=0, fillOpacity = 0.5) %>%
  addLegend(position="bottomright", pal = pal, values = ~var,
            title = NULL,
            opacity = 0.3)
mapdeck(token = Sys.getenv("mapbox_token"), style = mapdeck_style("dark")) %>%
  add_polygon(
    data = zones2plot
    , layer = "polygon_layer"
    , fill_colour = "var"
    , legend = TRUE
  )
