/* Table: Client  */
create table Client (
   client_id            INT4                 not null,
   client_phoneNumber   CHAR(11)             not null,
   client_orders        INT4                 not null,
   client_name          VARCHAR(128)         null,
   constraint PK_CLIENT primary key (client_id)
);

/* Index: Client_PK                                             */
create unique index Client_PK on Client (
client_id
);
/* Table: Equipment                                             */
create table Equipment (
   equipment_id         INT4                 not null,
   equipment_name       VARCHAR(128)         not null,
   equipment_status     VARCHAR(128)         not null,
   equipment_useCost    MONEY                null,
   constraint PK_EQUIPMENT primary key (equipment_id)
);

/* Index: Equipment_PK                                          */
create unique index Equipment_PK on Equipment (
equipment_id
);

/* Table: Manager                                               */
create table Manager (
   manager_id           INT4                 not null,
   manager_phoneNumber  CHAR(11)             not null,
   manager_name         VARCHAR(256)         not null,
   constraint PK_MANAGER primary key (manager_id)
);
/* Index: Manager_PK                                            */
create unique index Manager_PK on Manager (
manager_id
);
/* Table: Materials                                             */
create table Materials (
   material_id          INT4                 not null,
   servicesOrder_id     INT4                 not null,
   material_name        VARCHAR(128)         not null,
   material_amount      INT4                 not null,
   material_unit        VARCHAR(128)         not null,
   material_costUnit    MONEY                not null,
   total_cost           MONEY                GENERATED ALWAYS AS (material_amount * material_costUnit) STORED,
   constraint PK_MATERIALS primary key (material_id)
);
/* Index: Materials_PK                                          */
create unique index Materials_PK on Materials (
material_id
);
/* Index: Requires_FK                                           */
create  index Requires_FK on Materials (
servicesOrder_id
);
/* Table: Object                                                */
create table Object (
   object_id            INT4                 not null,
   object_type          VARCHAR(128)         not null,
   object_adress        VARCHAR(256)         not null,
   constraint PK_OBJECT primary key (object_id)
);
/* Index: Object_PK                                             */
create unique index Object_PK on Object (
object_id
);
/* Table: "Order"                                               */
create table "Order" (
   order_id             INT4                 not null,
   client_id            INT4                 not null,
   object_id            INT4                 not null,
   manager_id           INT4                 not null,
   order_startDate      DATE                 not null,
   order_endDate        DATE                 null,
   order_total          MONEY                not null,
   order_deadlines      CHAR(360)            null,
   order_status         VARCHAR(128)         not null,
   order_description    VARCHAR(256)         null,
   constraint PK_ORDER primary key (order_id)
);
/* Index: Order_PK                                              */
create unique index Order_PK on "Order" (
order_id
);
/* Index: Makes_FK                                              */
create  index Makes_FK on "Order" (
client_id
);
/* Index: Contains_FK                                           */
create  index Contains_FK on "Order" (
object_id
);
/* Index: Distributes_FK                                        */
create  index Distributes_FK on "Order" (
manager_id
);
/* Table: Perform                                               */
create table Perform (
   worker_id            INT4                 not null,
   servicesOrder_id     INT4                 not null,
   constraint PK_PERFORM primary key (worker_id, servicesOrder_id)
);
/* Index: Perform_PK                                            */
create unique index Perform_PK on Perform (
worker_id,
servicesOrder_id
);
/* Index: Perform2_FK                                           */
create  index Perform2_FK on Perform (
servicesOrder_id
);
/* Index: Perform_FK                                            */
create  index Perform_FK on Perform (
worker_id
);
/* Table: Require                                               */
create table Require (
   equipment_id         INT4                 not null,
   servicesOrder_id     INT4                 not null,
   constraint PK_REQUIRE primary key (equipment_id, servicesOrder_id)
);
/* Index: Require_PK                                            */
create unique index Require_PK on Require (
equipment_id,
servicesOrder_id
);
/* Index: Require2_FK                                           */
create  index Require2_FK on Require (
servicesOrder_id
);
/* Index: Require_FK                                            */
create  index Require_FK on Require (
equipment_id
);
/* Table: Service                                               */
create table Service (
   service_id           INT4                 not null,
   service_type         VARCHAR(128)         not null,
   service_cost         MONEY                not null,
   constraint PK_SERVICE primary key (service_id)
);
/* Index: Service_PK                                            */
create unique index Service_PK on Service (
service_id
);
/* Table: "Services in order"                                   */
create table "Services in order" (
   servicesOrder_id     INT4                 not null,
   order_id             INT4                 not null,
   service_id           INT4                 not null,
   servicesOrder_dateStart DATE                 not null,
   servicesOrder_dateEnd DATE                 not null,
   constraint "PK_SERVICES IN ORDER" primary key (servicesOrder_id)
);
/* Index: "Services in order_PK"                                */
create unique index "Services in order_PK" on "Services in order" (
servicesOrder_id
);
/* Index: Include_FK                                            */
create  index Include_FK on "Services in order" (
order_id
);
/* Index: Contain_FK                                            */
create  index Contain_FK on "Services in order" (
service_id
);
/* Table: Worker                                                */
create table Worker (
   worker_id            INT4                 not null,
   worker_status        VARCHAR(32)          not null,
   worker_specialization VARCHAR(128)         not null,
   worker_phoneNumber   CHAR(11)             not null,
   constraint PK_WORKER primary key (worker_id)
);
/* Index: Worker_PK                                             */
create unique index Worker_PK on Worker (
worker_id
);

alter table Materials
   add constraint FK_MATERIAL_REQUIRES_SERVICES foreign key (servicesOrder_id)
      references "Services in order" (servicesOrder_id)
      on delete cascade on update cascade;

alter table "Order"
   add constraint FK_ORDER_CONTAINS_OBJECT foreign key (object_id)
      references Object (object_id)
      on delete restrict on update cascade;

alter table "Order"
   add constraint FK_ORDER_DISTRIBUT_MANAGER foreign key (manager_id)
      references Manager (manager_id)
      on delete set null on update cascade;

alter table "Order"
   add constraint FK_ORDER_MAKES_CLIENT foreign key (client_id)
      references Client (client_id)
      on delete restrict on update cascade;

alter table Perform
   add constraint FK_PERFORM_PERFORM_WORKER foreign key (worker_id)
      references Worker (worker_id)
      on delete restrict on update cascade;

alter table Perform
   add constraint FK_PERFORM_PERFORM2_SERVICES foreign key (servicesOrder_id)
      references "Services in order" (servicesOrder_id)
      on delete cascade on update cascade;

alter table Require
   add constraint FK_REQUIRE_REQUIRE_EQUIPMEN foreign key (equipment_id)
      references Equipment (equipment_id)
      on delete restrict on update cascade;

alter table Require
   add constraint FK_REQUIRE_REQUIRE2_SERVICES foreign key (servicesOrder_id)
      references "Services in order" (servicesOrder_id)
      on delete cascade on update cascade;

alter table "Services in order"
   add constraint FK_SERVICES_CONTAIN_SERVICE foreign key (service_id)
      references Service (service_id)
      on delete restrict on update cascade;

alter table "Services in order"
   add constraint FK_SERVICES_INCLUDE_ORDER foreign key (order_id)
      references "Order" (order_id)
      on delete cascade on update cascade;
 
