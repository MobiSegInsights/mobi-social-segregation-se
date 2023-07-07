# Title     : Experienced/Visiting vs. residential income segregation
# Objective : Value difference as a function of residential income segregation
# Created by: Yuan Liao
# Created on: 2023-4-24

library(dplyr)
library(ggplot2)
library(ggpubr)
library(ggdensity)
library(arrow)
library(scales)
library(ggExtra)
library(yaml)
library(DBI)
options(scipen=10000)

#------------ Experienced segregion --------------
# Load all features
feature_dict <- list(weekend='Weekend', weekday='Weekday',
                     non_holiday='Non-holiday', holiday='Holiday',
                     number_of_locations='No. of unique locations visited',
                     number_of_visits='No. of visits',
                     average_displacement='Average displacement',
                     radius_of_gyration='Radius of gyration',
                     median_distance_from_home='Median distance from home',
                     `Not Sweden`='Prob. born outside Sweden',
                     `Lowest income group`='Prob. in lowest income group',
                     car_ownership='Prob. of owning a car',
                     cum_jobs='Job accessibility by car',
                     cum_stops='Transit accessibility by walking',
#                     evenness_income_resi='Residential income segregation',
                     ice_birth='Nativity segregation',
                     num_jobs='Job density at residence',
                     num_stops='Transit stop density at residence',
                     gsi='GSI at residence',
                     length_density='Pedestrian network density at residence')

df.vis <- as.data.frame(read_parquet('results/data4model_individual.parquet'))

fb.tre.low <- 0.4
fb.tre.high <- 0.1
df.vis$income_gp <- NA
df.vis$income_gp[df.vis$`Lowest income group` > fb.tre.low] <- "Low income"
df.vis$income_gp[df.vis$`Lowest income group` <= fb.tre.high] <- "High income"
#Remove rows with NA's using rowSums()
df.vis <- df.vis[rowSums(is.na(df.vis)) == 0, ]
df.vis$disparity <- df.vis$ice_birth - df.vis$ice_birth_resi

g1 <- ggplot(data=df.vis, aes(x=ice_birth_resi, y=disparity, color=income_gp)) +
  scale_color_manual(name='Income group',
                 breaks=c('High income', 'Low income'),
                 values=c('High income'='steelblue', 'Low income'='orange')) +
  geom_hdr_lines(show.legend = T) +
  #geom_point(size=1, alpha=0.7) +
  labs(y = 'Experienced - Residential', x = 'Residential nativity segregation') +
  theme_minimal() +
  theme(legend.position="top")

#------------ Visiting segregion --------------
df.deso <- as.data.frame(read_parquet('results/data4model_agg.parquet'))
df.deso$income_gp <- NA
df.deso$income_gp[df.deso$`Lowest income group` > fb.tre.low] <- "Low income"
df.deso$income_gp[df.deso$`Lowest income group` <= fb.tre.high] <- "High income"
#Remove rows with NA's using rowSums()
df.deso <- df.deso[rowSums(is.na(df.deso)) == 0, ]
df.deso$disparity <- df.deso$ice_birth - df.deso$ice_birth_resi

g2 <- ggplot(data=df.deso, aes(x=ice_birth_resi, y=disparity, color=income_gp)) +
  scale_color_manual(name='Income group',
                 breaks=c('High income', 'Low income'),
                 values=c('High income'='steelblue', 'Low income'='orange')) +
  geom_hdr_lines(show.legend = T) +
  #geom_point(size=1, alpha=0.7) +
  labs(y = 'Visiting - Residential', x = 'Residential nativity segregation') +
  theme_minimal() +
  theme(legend.position="top")

G <- ggarrange(g1, g2, common.legend = TRUE, legend="bottom",
               ncol = 2, nrow = 1, labels = c('(a)', '(b)'))
ggsave(filename = paste0("figures/", 'seg_disparity_ice.png'), plot=G,
       width = 10, height = 6, unit = "in", dpi = 300)