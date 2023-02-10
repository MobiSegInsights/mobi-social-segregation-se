# Title     : Experienced segregation vs. built environment
# Objective : Value difference on maps
# Created by: Yuan Liao
# Created on: 2023-2-9

library(dplyr)
library(ggplot2)
library(ggpubr)
library(sf)
library(geojsonsf)

# Static visualisation (Mobility vs. housing by region)
# region 1=Stockholm, 14=Gothenburg, 12=Malmö
geo <- geojson_sf("results/mobi_seg_spatio_static_built_env.geojson")
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
  geom_point(data=geo[geo$Foreign_background > fb.tre, ],
             aes(x=num_stops, y=S_background, color='>50%')) +
  geom_smooth(data=geo[geo$Foreign_background > fb.tre, ],
             aes(x=num_stops, y=S_background, color='>50%'),
             method='lm', formula= y~x) +
  geom_point(data=geo[geo$Foreign_background <= fb.tre, ],
             aes(x=num_stops, y=S_background, color='<=50%')) +
  geom_smooth(data=geo[geo$Foreign_background <= fb.tre, ],
             aes(x=num_stops, y=S_background, color='<=50%'),
             method='lm', formula= y~x) +
  ylim(0.05, 0.6) +
  scale_x_continuous(trans='log2') +
#  scale_y_continuous(trans='log2') +
  scale_color_manual(name='Share of foreign backgrounds',
                     breaks=c('>50%', '<=50%'),
                     values=c('>50%'='orange', '<=50%'='steelblue')) +
  labs(y = 'Unevenness of background', x = 'Transit stop density (/km^2)') +
  theme_minimal()

g2 <- ggplot() +
  geom_point(data=geo[geo$Foreign_background > fb.tre, ],
             aes(x=num_stops, y=S_income, color='>50%')) +
  geom_smooth(data=geo[geo$Foreign_background > fb.tre, ],
           aes(x=num_stops, y=S_income, color='>50%'),
           method='lm', formula= y~x) +
  geom_point(data=geo[geo$Foreign_background <= fb.tre, ],
           aes(x=num_stops, y=S_income, color='<=50%')) +
  geom_smooth(data=geo[geo$Foreign_background <= fb.tre, ],
           aes(x=num_stops, y=S_income, color='<=50%'),
           method='lm', formula= y~x) +
  ylim(0.05, 0.6) +
  scale_x_continuous(trans='log2') +
#  scale_y_continuous(trans='log2') +
  scale_color_manual(name='Share of foreign backgrounds',
                   breaks=c('>50%', '<=50%'),
                   values=c('>50%'='orange', '<=50%'='steelblue')) +
  labs(y = 'Unevenness of income', x = 'Transit stop density (/km^2)') +
  theme_minimal()

G <- ggarrange(g1, g2, ncol = 2, nrow = 1, labels = c('Unevenness of background', 'Unevenness of income'),
                common.legend = T, legend="top")
ggsave(filename = paste0("figures/", 'seg_built_env_working_days_relationship.png'), plot=G,
       width = 8, height = 5, unit = "in", dpi = 300)