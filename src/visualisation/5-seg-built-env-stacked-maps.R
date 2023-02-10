# Title     : Spatial patterns of segregation vs. built environment
# Objective : Three regions
# Created by: Yuan Liao
# Created on: 2023-02-09

library(assertthat)
library(purrr)
library(igraph)
library(ggplot2)
library(ggraph)
library(ggmap)
library(sp)
library(spdep)
library(dplyr)
library(stplanr)
library(ggnewscale)
library(geojsonsf)

rotate_data <- function(data, x_add = 0, y_add = 0) {

  shear_matrix <- function(){ matrix(c(2, 1.2, 0, 1), 2, 2) }

  rotate_matrix <- function(x){
    matrix(c(cos(x), sin(x), -sin(x), cos(x)), 2, 2)
  }
  data %>%
    dplyr::mutate(
      geometry = .$geometry * shear_matrix() * rotate_matrix(pi/20) + c(x_add, y_add)
    )
}

map.select <- function(geo, w, h, r){
  map2plot <- geo %>%
    filter(weekday==w,
           holiday==h,
           deso_3==r)
  return(map2plot)
}

geo <- geojson_sf("results/mobi_seg_spatio_static_built_env.geojson")
geo <- geo %>%
  rename('Foreign_background'='Foreign background',
         'Not_Sweden'='Not Sweden',
         'Lowest_income_group'='Lowest income group',
         'Foreign_background_h'='Foreign background_h',
         'Not_Sweden_h'='Not Sweden_h',
         'Lowest_income_group_h'='Lowest income group_h')

vars <- c('Unevenness of income', 'Unevenness of birth region', 'Unevenness of foreign background',
          'Foreign background', 'Not Sweden', 'Lowest income group',
          'Transit density', 'Ground space index', 'Number of health care services')
names(vars) <- c('S_income', 'S_birth_region', 'S_background',
                 "Foreign_background", "Not_Sweden", "Lowest_income_group",
                 'num_stops', 'gsi', 'hc_count')

regions <- c('Stockholm', 'Gothenburg', 'Malmo')
names(regions) <- c('01', '12', '14')

geo2plot <- map.select(geo=geo, w=1, h=0, r='01')

# annotate and plotting parameters
offset <- 0.8
xrange <- c(113, 120)
x <- 118.5
y <- 41.8
color <- 'gray40'
size.ft <- 2

g1 <- ggplot() +
  geom_sf(data=geo2plot %>% rotate_data, aes_string(fill='S_income'), inherit.aes = FALSE,
          color = NA, alpha=0.7, show.legend = F) +
  scale_fill_gradient(low = "green", high = "red") +
  annotate("text", label='Unevenness of income', x=x, y=y, hjust = 0, color=color, size=size.ft)

g2 <- g1 +
  new_scale_fill() +
  geom_sf(data=geo2plot %>% rotate_data(y_add = offset), aes_string(fill='Lowest_income_group'), inherit.aes = FALSE,
          color = NA, alpha=0.7, show.legend = F) +
  scale_fill_gradient(low = "green", high = "red") +
  annotate("text", label='Lowest income group', x=x, y=y+offset, hjust = 0, color=color, size=size.ft)

g3 <- g2 +
  new_scale_fill() +
  geom_sf(data=geo2plot %>% rotate_data(y_add = offset * 2), aes_string(fill='num_stops'), inherit.aes = FALSE,
          color = NA, alpha=0.7, show.legend = F) +
  scale_fill_viridis(trans = 'log') +
  annotate("text", label='Transit density', x=x, y=y+offset*2, hjust = 0, color=color, size=size.ft)

g4 <- g3 +
  new_scale_fill() +
  geom_sf(data=geo2plot %>% rotate_data(y_add = offset * 3), aes_string(fill='gsi'), inherit.aes = FALSE,
          color = NA, alpha=0.7, show.legend = F) +
  scale_fill_viridis(trans = 'log') +
  annotate("text", label='Ground space index', x=x, y=y+offset*3, hjust = 0, color=color, size=size.ft)

g5 <- g4 +
  new_scale_fill() +
  geom_sf(data=geo2plot %>% rotate_data(y_add = offset * 4), aes_string(fill='hc_count'), inherit.aes = FALSE,
          color = NA, alpha=0.7, show.legend = F) +
  scale_fill_viridis(trans = 'log') +
  annotate("text", label='Health-care service count', x=x, y=y+offset*4, hjust = 0, color=color, size=size.ft) +
  labs(title = 'Stockholm') +
  theme_void() +
  scale_x_continuous(limits = xrange)

w <- 12
h <- 8
ggsave(filename = "figures/stacked_stockholm.png", plot=g5,
       width = w, height = h, unit = "cm", dpi = 300)