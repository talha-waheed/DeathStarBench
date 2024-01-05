package dialer

import (
	"context"
	"fmt"
	"google.golang.org/grpc/metadata"
	"time"

	"github.com/delimitrou/DeathStarBench/hotelreservation/tls"
	consul "github.com/hashicorp/consul/api"
	lb "github.com/olivere/grpc/lb/consul"
	opentracing "github.com/opentracing/opentracing-go"
	"google.golang.org/grpc"
	"google.golang.org/grpc/keepalive"
)

// DialOption allows optional config for dialer
type DialOption func(name string) (grpc.DialOption, error)

func UnaryClientInterceptor(
	ctx context.Context,
	method string,
	req, reply interface{},
	cc *grpc.ClientConn,
	invoker grpc.UnaryInvoker,
	opts ...grpc.CallOption) error {
	// Take the incoming metadata and transfer it to the outgoing metadata
	if md, ok := metadata.FromIncomingContext(ctx); ok {
		ctx = metadata.NewOutgoingContext(ctx, md)
	}
	return invoker(ctx, method, req, reply, cc, opts...)
}

// WithTracer traces rpc calls
func WithTracer(tracer opentracing.Tracer) DialOption {
	return func(name string) (grpc.DialOption, error) {
		return grpc.WithUnaryInterceptor(UnaryClientInterceptor), nil
	}
	//return func(name string) (grpc.DialOption, error) {
	//	return grpc.WithUnaryInterceptor(otgrpc.OpenTracingClientInterceptor(tracer)), nil
	//}
}

// WithBalancer enables client side load balancing
func WithBalancer(registry *consul.Client) DialOption {
	return func(name string) (grpc.DialOption, error) {
		r, err := lb.NewResolver(registry, name, "")
		if err != nil {
			return nil, err
		}
		return grpc.WithBalancer(grpc.RoundRobin(r)), nil
	}
}

// Dial returns a load balanced grpc client conn with tracing interceptor
func Dial(name string, opts ...DialOption) (*grpc.ClientConn, error) {

	dialopts := []grpc.DialOption{
		grpc.WithKeepaliveParams(keepalive.ClientParameters{
			Timeout:             120 * time.Second,
			PermitWithoutStream: true,
		}),
	}
	if tlsopt := tls.GetDialOpt(); tlsopt != nil {
		dialopts = append(dialopts, tlsopt)
	} else {
		dialopts = append(dialopts, grpc.WithInsecure())
	}

	for _, fn := range opts {
		opt, err := fn(name)
		if err != nil {
			return nil, fmt.Errorf("config error: %v", err)
		}
		dialopts = append(dialopts, opt)
	}

	conn, err := grpc.Dial(name, dialopts...)
	if err != nil {
		return nil, fmt.Errorf("failed to dial %s: %v", name, err)
	}

	return conn, nil
}
