# Title     : Visiting vs. housing segregation on
# Objective : Value difference on maps
# Created by: Yuan Liao
# Created on: 2023-2-3

library(dplyr)
library(ggplot2)
library(ggExtra)
library(sf)
library(geojsonsf)
library(ggdensity)
library(cowplot)
options(scipen=10000)


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
geo$income_gp <- NA
geo$income_gp[geo$Lowest_income_group_h > fb.tre] <- ">25%"
geo$income_gp[geo$Lowest_income_group_h <= fb.tre] <- "<=25%"

upper <- max(c(max(geo$evenness_income_h), max(geo$evenness_income)))
g1 <- ggplot(data=geo, aes(x=evenness_income_h, y=evenness_income, color=income_gp)) +
  scale_color_manual(name='Share of lowest-income group',
                 breaks=c('>25%', '<=25%'),
                 values=c('>25%'='orange', '<=25%'='steelblue')) +
  geom_abline(intercept = 0, slope = 1, color='gray75') +
  geom_point(size=1, alpha=0.7) +
  xlim(0, upper) +
  ylim(0, upper) +
  labs(title = 'Unevenness of income', y = 'Visiting', x = 'Housing') +
  theme_minimal() +
  theme(legend.position="none")
g1 <- ggMarginal(g1, type = "density", groupFill = TRUE, groupColour = TRUE)


upper <- max(c(max(geo$Foreign_background_h), max(geo$Foreign_background)))
g2 <- ggplot(data=geo, aes(x=Foreign_background_h, y=Foreign_background, color=income_gp)) +
  scale_color_manual(name='Share of lowest-income group',
                 breaks=c('>25%', '<=25%'),
                 values=c('>25%'='orange', '<=25%'='steelblue')) +
  geom_abline(intercept = 0, slope = 1, color='gray75') +
  geom_point(size=1, alpha=0.7) +
  xlim(0, upper) +
  ylim(0, upper) +
  labs(title = 'Share of foreign\nbackground', y = 'Visiting', x = 'Housing') +
  theme_minimal() +
  theme(legend.position="none")
g2 <- ggMarginal(g2, type = "density", groupFill = TRUE, groupColour = TRUE)


upper <- max(c(max(geo$radius_of_gyration_h), max(geo$radius_of_gyration)))
g3 <- ggplot(data=geo, aes(x=radius_of_gyration_h, y=radius_of_gyration, color=income_gp)) +
  scale_color_manual(name='Share of lowest-income group',
                 breaks=c('>25%', '<=25%'),
                 values=c('>25%'='orange', '<=25%'='steelblue')) +
  geom_abline(intercept = 0, slope = 1, color='gray75') +
  geom_point(size=1, alpha=0.7) +
  scale_x_log10(limits=c(0.1, 1000)) +
  scale_y_log10(limits=c(0.1, 1000)) +
  labs(title = 'Radius of gyration (km)', y = 'Visiting', x = 'Housing') +
  theme_minimal() +
  theme(legend.position="none")
g3 <- ggMarginal(g3, type = "density", groupFill = TRUE, groupColour = TRUE)

G <- plot_grid(g1, g2, g3, labels=c("(a)", "(b)", "(c)"), ncol = 3, nrow = 1)

# legend_b <- get_legend(
#   g1 + theme(legend.position = "bottom")
# )
# G <- plot_grid(G, legend_b, ncol=1, rel_heights = c(1, .1))

ggsave(filename = paste0("figures/", 'mobi_seg_comp.png'), plot=G,
       width = 9, height = 3, unit = "in", dpi = 300)