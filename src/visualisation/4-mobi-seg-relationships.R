# Title     : Experienced vs. housing segregation on
# Objective : Value difference on maps
# Created by: Yuan Liao
# Created on: 2023-2-3

library(dplyr)
library(ggplot2)
library(ggpubr)
library(sf)
library(geojsonsf)

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

fb.tre <- 0.5
# g0 <- ggplot() +
#   geom_point(data=geo[geo$Lowest_income_group_h > fb.tre, ],
#              aes(x=S_background_h, y=S_background), color='red') +
#   geom_point(data=geo[geo$Lowest_income_group_h <= fb.tre, ],
#              aes(x=S_background_h, y=S_background), color='darkblue') +
#   theme_minimal()


g1 <- ggplot() +
  geom_point(data=geo[geo$Foreign_background_h > fb.tre, ],
             aes(x=S_background_h, y=Lowest_income_group_h, color='>50%')) +
  geom_smooth(data=geo[geo$Foreign_background_h > fb.tre, ],
             aes(x=S_background_h, y=Lowest_income_group_h, color='>50%'),
             method='lm', formula= y~x) +
  geom_point(data=geo[geo$Foreign_background_h <= fb.tre, ],
             aes(x=S_background_h, y=Lowest_income_group_h, color='<=50%')) +
  geom_smooth(data=geo[geo$Foreign_background_h <= fb.tre, ],
             aes(x=S_background_h, y=Lowest_income_group_h, color='<=50%'),
             method='lm', formula= y~x) +
  ylim(0.05, 0.6) +
  scale_color_manual(name='Share of foreign backgrounds',
                     breaks=c('>50%', '<=50%'),
                     values=c('>50%'='orange', '<=50%'='steelblue')) +
  labs(x = 'Unevenness of background', y = 'Share of lowest income group') +
  theme_minimal()

g2 <- ggplot() +
  geom_point(data=geo[geo$Foreign_background > fb.tre, ],
             aes(x=S_background, y=Lowest_income_group, color='>50%')) +
  geom_smooth(data=geo[geo$Foreign_background > fb.tre, ],
           aes(x=S_background, y=Lowest_income_group, color='>50%'),
           method='lm', formula= y~x) +
  geom_point(data=geo[geo$Foreign_background <= fb.tre, ],
           aes(x=S_background, y=Lowest_income_group, color='<=50%')) +
  geom_smooth(data=geo[geo$Foreign_background <= fb.tre, ],
           aes(x=S_background, y=Lowest_income_group, color='<=50%'),
           method='lm', formula= y~x) +
  ylim(0.05, 0.6) +
  scale_color_manual(name='Share of foreign backgrounds',
                   breaks=c('>50%', '<=50%'),
                   values=c('>50%'='orange', '<=50%'='steelblue')) +
  labs(x = 'Unevenness of background', y = 'Share of lowest income group') +
  theme_minimal()

G <- ggarrange(g1, g2, ncol = 2, nrow = 1, labels = c('Housing', 'Experienced'),
                common.legend = T, legend="top")
ggsave(filename = paste0("figures/", 'mobi_seg_working_days_relationship.png'), plot=G,
       width = 8, height = 5, unit = "in", dpi = 300)