# Title     : Population representation and temporal distribution
# Objective : Two biases
# Created by: Yuan Liao
# Created on: 2023-02-14

library(dplyr)
library(ggplot2)
library(ggsci)
library(ggpubr)
library(ggspatial)
library(sf)
library(ggraph)
library(scico)
library(yaml)
library(DBI)
library(scales)

# Load temporal profile
df.tempo <- read.csv('results/activity_patterns_mad.csv')
df.tempo$activity <- plyr::mapvalues(df.tempo$activity,
                                        from=c('all', 'holiday', 'non_holiday'),
                                        to=c("Total","Holiday","Non-holiday"))
g1 <- ggplot(data = df.tempo) +
  geom_line(aes(x = half_hour / 2, y = freq/1000000,
                group = activity, color = activity)) +
  scale_color_discrete(name = 'Type') +
  labs(x = 'Hour of day', y = 'Number of stays (million)') +
  scale_y_continuous() +
  theme_minimal() +
  theme(plot.margin = margin(1,1,0,0, "cm"),
        legend.position = 'top')

# Load detected home from the database
keys_manager <- read_yaml('./dbs/keys.yaml')
user <- keys_manager$database$user
password <- keys_manager$database$password
port <- keys_manager$database$port
db_name <- keys_manager$database$name
con <- DBI::dbConnect(RPostgres::Postgres(),
                      host = "localhost",
                      dbname = db_name,
                      user = user,
                      password = password,
                      port = port)
df <- dbGetQuery(con, 'SELECT * FROM public.home_sub')
zones <- read_sf('dbs/DeSO/DeSO_2018_v2.shp')[, c('deso', 'befolkning', 'geometry')]
df.pop <- df %>%
  group_by(deso) %>%
  count()
zones.pop <- merge(zones, df.pop, on='deso')
zones.pop <- zones.pop %>%
  mutate(pop_share = n/befolkning*100)

g2 <- ggplot(zones.pop) + # [zones.pop$pop_share < 100,]
  geom_point(aes(x=befolkning, y=n), show.legend = F,
             alpha=0.7, size=0.3, color='steelblue') +
  labs(x='Population', y='Mobile users') +
  scale_x_log10(limits = c(min(zones.pop$befolkning), max(zones.pop$befolkning)),
                breaks = trans_breaks("log10", function(x) 10^x),
                labels = trans_format("log10", math_format(10^.x))) +
  scale_y_log10(limits = c(1, max(zones.pop$befolkning)),
                breaks = trans_breaks("log10", function(x) 10^x),
                labels = trans_format("log10", math_format(10^.x))) +
  annotation_logticks() +
  theme_minimal() +
  theme(plot.margin = margin(1,0,0,0, "cm"))

# my_breaks <- c(0.05, 0.1, 1, 5, 20, 200)
# g3 <- ggplot(zones.pop) +
#   geom_sf(aes(fill=pop_share), color = NA, alpha=1, show.legend = T) +
#   scale_fill_gradient(low = "darkblue", high = "yellow", trans = "log",
#                       name='Mobile users / pop. (%)',
#                       breaks = my_breaks, labels = my_breaks) +
#   coord_sf(datum=st_crs(3006)) +
#   theme(legend.position = 'bottom') +
#   annotation_scale() +
#   theme_void() +
#   theme(plot.margin = margin(0.5,1,0,0, "cm"),
#         legend.position = 'top')
#
# G <- ggarrange(g1, g2, g3, ncol = 3, nrow = 1,
#                labels = c('(d)', '(e)', '(f)'),
#                widths = c(1.2, 1.2, 1))
# ggsave(filename = "figures/data_biases.png", plot=G,
#        width = 9, height = 4, unit = "in", dpi = 300)

G <- ggarrange(g1, g2, ncol = 2, nrow = 1,
               labels = c('(d)', '(e)'),
               widths = c(1, 1))
ggsave(filename = "figures/data_biases.png", plot=G,
       width = 8, height = 4, unit = "in", dpi = 300)