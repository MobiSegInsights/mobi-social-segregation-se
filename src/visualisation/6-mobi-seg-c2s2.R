# Title     : Main results display for C2S2 conference 2023
# Objective : (a) Seg. in Stockholm, (b) Visiting vs. housing seg, (c)
# Created by: Yuan Liao
# Created on: 2023-02-21

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
library(ggdensity)
library(tidyr)
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
         'Lowest_income_group_h'='Lowest income group_h') %>%
  filter(weekday==1, holiday==0)

fb.tre <- 0.25
geo$income_gp <- NA
geo$income_gp[geo$Lowest_income_group_h > fb.tre] <- "Less wealthy"
geo$income_gp[geo$Lowest_income_group_h <= fb.tre] <- "Wealthy"

#------------------ (a) Unevenness of income in Stockholm
map.select <- function(geo, r){
  map2plot <- geo %>%
    filter(deso_3==r)
  return(map2plot)
}

get.basemap <- function(geoframe){
  # Get basemap as the background
  bbox <- st_bbox(geoframe)
  names(bbox) <- c("left", "bottom", "right", "top")
  bmap <- get_stamenmap(bbox, maptype="toner-lite", zoom = 10)
  return(bmap)
}

segregation.mapping <- function(geo2plot, var1, var2, vname, bmap){
  g1 <- ggmap(bmap) +
    geom_sf(data=geo2plot, aes_string(fill=var1), inherit.aes = FALSE,
            color = NA, alpha=0.7, show.legend = T)
  g2 <- ggmap(bmap) +
    geom_sf(data=geo2plot, aes_string(fill=var2), inherit.aes = FALSE,
            color = NA, alpha=0.7, show.legend = T)
  g1 <- g1 +
    scale_fill_gradient(low = "cyan3", high = "coral2", name=vname)
  g2 <- g2 +
    scale_fill_gradient(low = "cyan3", high = "coral2", name=vname)
  g1 <- g1 +
    labs(title = 'Visiting') +
    theme_void() +
    theme(legend.position = 'top', legend.key.height = unit(0.5, "cm"),
          plot.margin = margin(0.5,0.2,0.2,0, "cm"))
  g2 <- g2 +
    labs(title = 'Residential') +
    theme_void() +
    theme(legend.position = 'top', legend.key.height = unit(0.5, "cm"),
          plot.margin = margin(0.5,0.2,0.2,0, "cm"))

  G <- ggarrange(g1, g2, ncol = 2, nrow = 1, common.legend = T, legend="top")
  return(G)
}

vars <- c('Unevenness of income', 'Lowest income group', 'Foreign background', "Radius of gyration (km)")
names(vars) <- c('evenness_income', "Lowest_income_group", "Foreign_background", "radius_of_gyration")

regions <- c('Stockholm', 'Gothenburg', 'Malmo')
names(regions) <- c('01', '14', '12')

# Weekday, non-holiday
geo2plot <- map.select(geo=geo, r='01')
bmap <- get.basemap(geo2plot)
g1 <- segregation.mapping(geo=geo2plot, var1='evenness_income_r',
                          var2='evenness_income_h',
                          vname='Unevenness of income', bmap=bmap)

# ------------------ (b) Unevenness of income: visiting vs. residential
GeomSplitViolin <- ggproto("GeomSplitViolin", GeomViolin,
                           draw_group = function(self, data, ..., draw_quantiles = NULL) {
  data <- transform(data, xminv = x - violinwidth * (x - xmin), xmaxv = x + violinwidth * (xmax - x))
  grp <- data[1, "group"]
  newdata <- plyr::arrange(transform(data, x = if (grp %% 2 == 1) xminv else xmaxv), if (grp %% 2 == 1) y else -y)
  newdata <- rbind(newdata[1, ], newdata, newdata[nrow(newdata), ], newdata[1, ])
  newdata[c(1, nrow(newdata) - 1, nrow(newdata)), "x"] <- round(newdata[1, "x"])

  if (length(draw_quantiles) > 0 & !scales::zero_range(range(data$y))) {
    stopifnot(all(draw_quantiles >= 0), all(draw_quantiles <=
      1))
    quantiles <- ggplot2:::create_quantile_segment_frame(data, draw_quantiles)
    aesthetics <- data[rep(1, nrow(quantiles)), setdiff(names(data), c("x", "y")), drop = FALSE]
    aesthetics$alpha <- rep(1, nrow(quantiles))
    both <- cbind(quantiles, aesthetics)
    quantile_grob <- GeomPath$draw_panel(both, ...)
    ggplot2:::ggname("geom_split_violin", grid::grobTree(GeomPolygon$draw_panel(newdata, ...), quantile_grob))
  }
  else {
    ggplot2:::ggname("geom_split_violin", GeomPolygon$draw_panel(newdata, ...))
  }
})

geom_split_violin <- function(mapping = NULL, data = NULL, stat = "ydensity", position = "identity", ...,
                              draw_quantiles = NULL, trim = TRUE, scale = "area", na.rm = FALSE,
                              show.legend = NA, inherit.aes = TRUE) {
  layer(data = data, mapping = mapping, stat = stat, geom = GeomSplitViolin,
        position = position, show.legend = show.legend, inherit.aes = inherit.aes,
        params = list(trim = trim, scale = scale, draw_quantiles = draw_quantiles, na.rm = na.rm, ...))
}
geo2plot1 <- geo[,c('evenness_income_r', 'income_gp')] %>%
  rename('evenness_income'='evenness_income_r') %>%
  mutate(Type='Visiting')
geo2plot2 <- geo[,c('evenness_income_h', 'income_gp')] %>%
  rename('evenness_income'='evenness_income_h') %>%
  mutate(Type='Residential')
geo2plot <- rbind(geo2plot1, geo2plot2)

g2 <- ggplot(geo2plot, aes(x = Type, y = evenness_income, fill = income_gp)) +
  geom_split_violin(alpha = .4, trim = FALSE) +
  geom_boxplot(width = .15, alpha = .6, fatten = NULL, show.legend = FALSE, linewidth=0.2) +
  stat_summary(fun.data = "mean_cl_normal", fun.args=list(conf.int=0.95),
               geom = "pointrange", show.legend = F, size=0.1, linewidth=0.5,
               position = position_dodge(.1), color='white') +
  labs(y = 'Unevenness of income', x = 'Segregation measure') +
  theme_minimal() +
  scale_fill_manual(name='Income level',
               breaks=c('Less wealthy', 'Wealthy'),
               values=c('Less wealthy'='orange', 'Wealthy'='steelblue')) +
  theme(legend.position="top")

# ------------------ (c) Unevenness of income vs. foreign background
geo.c <- geo[,c('evenness_income_r', 'Foreign_background', 'income_gp')] %>%
  rename('evenness_income'='evenness_income_r') %>%
  mutate(Type='Visiting',
         Foreign_background=Foreign_background*100)
qtls <- lapply(c(0, 20, 40, 60, 80, 85, 90, 95, 100),
               function(x){quantile(geo.c$Foreign_background, x/100)})
lbls <- names(unlist(qtls))
geo.c$fb_gp <- cut(geo.c$Foreign_background, breaks = qtls)
geo.c <- drop_na(geo.c)

ethni.seg.plot <- function(data.low, data.high, pt.size){
  g1 <- ggplot(data=data.low, aes(x=Foreign_background, y=evenness_income)) +
    geom_hdr(fill='orange', show.legend = F) +
    geom_point(color='orange', size=pt.size) +
    xlim(0, 1) +
    ylim(0, 0.6) +
    labs(title = 'Income level: Less wealthy', y = 'Unevenness of income', x = 'Share of foreign background') +
    theme_minimal()

  g2 <- ggplot(data=data.high, aes(x=Foreign_background, y=evenness_income)) +
    geom_hdr(fill='steelblue', show.legend = F) +
    geom_point(color='steelblue', size=pt.size) +
    xlim(0, 1) +
    ylim(0, 0.6) +
    labs(title = 'Wealthy', y = '', x = 'Share of foreign background') +
    theme_minimal()

  G <- ggarrange(g1, g2, ncol = 2, nrow = 1)
  return(G)
}

#g3 <- ethni.seg.plot(data.low = geo.c[geo.c$income_gp=='Less wealthy', ],
#                     data.high = geo.c[geo.c$income_gp=='Wealthy', ], 0.8)

g3 <- ggplot(geo.c, aes(x = fb_gp, y = evenness_income, fill = income_gp)) +
  geom_split_violin(alpha = .4, trim = FALSE) +
  geom_boxplot(width = .15, alpha = .6, fatten = NULL, show.legend = FALSE, linewidth=0.2) +
  stat_summary(fun.data = "mean_cl_normal", fun.args=list(conf.int=0.95),
               geom = "pointrange", show.legend = F, size=0.1, linewidth=0.5,
               position = position_dodge(.1), color='white') +
  labs(y = 'Unevenness of income', x = 'Share of foreign background (%)') +
  theme_minimal() +
  scale_fill_manual(name='Income level',
               breaks=c('Less wealthy', 'Wealthy'),
               values=c('Less wealthy'='orange', 'Wealthy'='steelblue')) +
  theme(legend.position="top")

G1 <- ggarrange(g1, g2, ncol = 2, nrow = 1, labels = c('(a)', '(b)'))
G <- ggarrange(G1, g3, ncol = 1, nrow = 2, labels = c('', '(c)'))
ggsave(filename = paste0("figures/", 'mobi_seg_results.png'), plot=G,
       width = 8, height = 8, unit = "in", dpi = 300)
